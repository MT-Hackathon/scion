#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = ["pyyaml>=6.0"]
# ///
"""
Analyze recurring conversation failure patterns against skill/rule coverage.

This analysis is heuristic. It relies on keyword markers for failures and domain
classification rather than semantic understanding of message intent.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

import db_utils

if all(
    hasattr(db_utils, name)
    for name in ("find_cursor_db", "get_connection", "get_conversations")
):
    find_cursor_db = getattr(db_utils, "find_cursor_db")
    get_connection = getattr(db_utils, "get_connection")
    get_conversations = getattr(db_utils, "get_conversations")
else:
    from db_utils import (
        extract_conversations,
        get_cursor_db_path,
        get_conversation_date,
        is_project_conversation,
        load_database,
    )

    def find_cursor_db() -> Path:
        db_path = get_cursor_db_path()
        if not db_path:
            raise FileNotFoundError("Cursor database path could not be detected.")
        return Path(db_path)

    def get_connection(db_path: Path | str):
        return load_database(str(db_path))

    def get_conversations(conn, project_path: str | None = None):
        conversations = extract_conversations(conn)
        items: list[dict[str, Any]] = []
        for conv_id, messages in conversations.items():
            items.append(
                {
                    "id": conv_id,
                    "messages": messages,
                    "timestamp": get_conversation_date(messages),
                }
            )
        if project_path:
            items = [
                item
                for item in items
                if is_project_conversation(item["messages"], project_path)
            ]
        items.sort(
            key=lambda item: item.get("timestamp") or 0,
            reverse=True,
        )
        return items


CORRECTION_MARKERS = [
    "actually",
    "no,",
    "that's not right",
    "let me fix",
    "sorry",
]
RETRY_MARKERS = [
    "try again",
    "let's try",
    "attempt",
    "still failing",
]
ERROR_MARKERS = [
    "error",
    "exception",
    "traceback",
    "failed",
]
ALL_MARKERS = CORRECTION_MARKERS + RETRY_MARKERS + ERROR_MARKERS

DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "testing": ["test", "pytest", "vitest", "assert", "coverage"],
    "security": ["auth", "oauth", "jwt", "token", "credential", "security"],
    "styling": ["css", "style", "theme", "layout", "ui", "responsive"],
    "api": ["api", "endpoint", "request", "response", "http", "rest"],
    "database": ["database", "sql", "query", "migration", "postgres", "sqlite"],
    "build": ["build", "compile", "lint", "typecheck", "bundl", "warning"],
    "deployment": ["deploy", "release", "pipeline", "ci", "cd", "container"],
    "configuration": ["config", "env", "setting", "variable", "path", "setup"],
    "refactoring": ["refactor", "rename", "move", "cleanup", "restructure"],
    "accessibility": ["a11y", "accessibility", "aria", "screen reader", "wcag"],
}


@dataclass(frozen=True)
class KnowledgeArtifact:
    name: str
    kind: str
    description: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze skill/rule coverage against recurring failure patterns."
    )
    parser.add_argument(
        "--project",
        "-p",
        help="Optional project path filter for conversations.",
    )
    parser.add_argument(
        "--sessions",
        "-n",
        type=int,
        default=20,
        help="Number of recent sessions to analyze (default: 20).",
    )
    parser.add_argument(
        "--cursor-dir",
        type=Path,
        default=None,
        help="Path to .cursor directory (default: auto-detect).",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text).",
    )
    args = parser.parse_args()
    if args.sessions < 1:
        parser.error("--sessions must be >= 1")
    return args


def detect_cursor_dir(explicit_path: Path | None) -> Path:
    if explicit_path:
        cursor_dir = explicit_path.expanduser().resolve()
        if not cursor_dir.is_dir():
            raise FileNotFoundError(f"Cursor directory not found: {cursor_dir}")
        return cursor_dir
    inferred = Path(__file__).resolve().parent.parent.parent.parent
    if inferred.is_dir() and inferred.name == ".cursor":
        return inferred
    raise FileNotFoundError("Unable to auto-detect .cursor directory.")


def parse_frontmatter(file_path: Path) -> dict[str, Any]:
    text = file_path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    try:
        end = text.index("---", 3)
    except ValueError:
        return {}
    raw = text[3:end]
    parsed = yaml.safe_load(raw)
    if isinstance(parsed, dict):
        return parsed
    return {}


def extract_first_heading(file_path: Path) -> str:
    text = file_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    in_frontmatter = False
    for line in lines:
        if line.strip() == "---":
            in_frontmatter = not in_frontmatter
            continue
        if in_frontmatter:
            continue
        if line.startswith("#"):
            return line.lstrip("#").strip()
    return ""


def load_knowledge_artifacts(cursor_dir: Path) -> list[KnowledgeArtifact]:
    skills_dir = cursor_dir / "skills"
    rules_dir = cursor_dir / "rules"
    artifacts: list[KnowledgeArtifact] = []

    if skills_dir.is_dir():
        for skill_dir in sorted(skills_dir.iterdir()):
            skill_file = skill_dir / "SKILL.md"
            if not skill_dir.is_dir() or not skill_file.exists():
                continue
            fm = parse_frontmatter(skill_file)
            name = str(fm.get("name") or skill_dir.name)
            description = str(fm.get("description") or "").strip()
            if not description:
                description = extract_first_heading(skill_file)
            artifacts.append(KnowledgeArtifact(name=name, kind="skill", description=description))

    if rules_dir.is_dir():
        for rule_dir in sorted(rules_dir.iterdir()):
            if not rule_dir.is_dir():
                continue
            rule_file = rule_dir / "RULE.mdc"
            if not rule_file.exists():
                continue
            fm = parse_frontmatter(rule_file)
            name = str(fm.get("name") or rule_dir.name)
            description = str(fm.get("description") or "").strip()
            if not description:
                description = extract_first_heading(rule_file)
            artifacts.append(KnowledgeArtifact(name=name, kind="rule", description=description))

    return artifacts


def _conversation_to_messages(conversations: Any) -> list[list[dict[str, Any]]]:
    if isinstance(conversations, dict):
        return [messages for messages in conversations.values() if isinstance(messages, list)]
    if not isinstance(conversations, list):
        return []
    normalized: list[list[dict[str, Any]]] = []
    for item in conversations:
        if isinstance(item, dict) and isinstance(item.get("messages"), list):
            normalized.append(item["messages"])
    return normalized


def get_recent_conversations(
    conn: Any,
    project: str | None,
    sessions: int,
) -> list[list[dict[str, Any]]]:
    conversations = get_conversations(conn, project_path=project)
    normalized = _conversation_to_messages(conversations)
    return normalized[:sessions]


def normalize_text(text: str) -> str:
    lowered = text.lower()
    return re.sub(r"\s+", " ", lowered).strip()


def extract_message_text(message: dict[str, Any]) -> str:
    data = message.get("data")
    if not isinstance(data, dict):
        return ""
    parts: list[str] = []
    text = data.get("text")
    if isinstance(text, str) and text.strip():
        parts.append(text)
    rich_text = data.get("richText")
    if rich_text:
        parts.append(str(rich_text))
    return " ".join(parts)


def classify_domains(text: str) -> list[str]:
    normalized = normalize_text(text)
    if not normalized:
        return []
    matches: list[str] = []
    for domain, keywords in DOMAIN_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            matches.append(domain)
    if matches:
        return matches
    return ["configuration"]


def detect_failure_events(conversations: list[list[dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    by_domain: dict[str, dict[str, Any]] = {
        domain: {"count": 0, "examples": []} for domain in DOMAIN_KEYWORDS
    }

    for messages in conversations:
        for message in messages:
            text = extract_message_text(message)
            normalized = normalize_text(text)
            if not normalized:
                continue
            if not any(marker in normalized for marker in ALL_MARKERS):
                continue
            domains = classify_domains(text)
            excerpt = text.strip().replace("\n", " ")[:180]
            for domain in domains:
                if domain not in by_domain:
                    by_domain[domain] = {"count": 0, "examples": []}
                by_domain[domain]["count"] += 1
                if len(by_domain[domain]["examples"]) < 3 and excerpt:
                    by_domain[domain]["examples"].append(excerpt)
    return by_domain


def compute_coverage(
    artifacts: list[KnowledgeArtifact],
    failure_by_domain: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for domain, details in failure_by_domain.items():
        failures = int(details.get("count", 0))
        if failures < 1:
            continue
        keywords = DOMAIN_KEYWORDS.get(domain, [domain])
        covered_by = [
            artifact.name
            for artifact in artifacts
            if any(keyword in artifact.description.lower() for keyword in keywords)
        ]
        coverage_count = len(set(covered_by))
        gap_score = failures * (1.0 / (coverage_count + 1))
        rows.append(
            {
                "domain": domain,
                "failures": failures,
                "covered_by": sorted(set(covered_by)),
                "coverage_count": coverage_count,
                "gap_score": round(gap_score, 3),
                "example": (details.get("examples") or [""])[0],
            }
        )
    rows.sort(key=lambda row: (row["gap_score"], row["failures"]), reverse=True)
    return rows


def coverage_percent(rows: list[dict[str, Any]]) -> float:
    if not rows:
        return 0.0
    covered = sum(1 for row in rows if row["coverage_count"] > 0)
    return (covered / len(rows)) * 100.0


def build_recommendation(row: dict[str, Any]) -> str:
    domain = row["domain"]
    covered_by = row["covered_by"]
    if covered_by:
        return f"Update {covered_by[0]} to address repeated {domain} failure patterns"
    return f"Create new skill for {domain} failure prevention and debugging patterns"


def render_text_report(
    sessions: int,
    total_events: int,
    rows: list[dict[str, Any]],
) -> str:
    gap_rows = [row for row in rows if row["coverage_count"] <= 1]
    covered_rows = [row for row in rows if row["coverage_count"] >= 2]
    lines = [
        "Skill Gap Analysis",
        "==================",
        f"Sessions analyzed: {sessions}",
        f"Failure events detected: {total_events}",
        "",
        "Top Knowledge Gaps:",
    ]
    if not gap_rows:
        lines.append("None detected in analyzed sessions.")
    else:
        for idx, row in enumerate(gap_rows[:10], start=1):
            coverage = ", ".join(row["covered_by"]) if row["covered_by"] else "NO COVERAGE"
            lines.append(
                f"{idx}. {row['domain']} - {row['failures']} failures, covered by: {coverage}"
            )
            if row["example"]:
                lines.append(f'   Example: "{row["example"]}"')
            lines.append(f"   Recommendation: {build_recommendation(row)}")
            lines.append("")

    lines.append("Well-Covered Domains:")
    if not covered_rows:
        lines.append("- None")
    else:
        for row in covered_rows:
            lines.append(
                f"- {row['domain']}: {row['failures']} failures, covered by "
                f"{', '.join(row['covered_by'])}"
            )

    lines.extend(
        [
            "",
            "Coverage Summary:",
            f"- Domains with gaps: {len(gap_rows)}",
            f"- Domains well-covered: {len(covered_rows)}",
            f"- Overall coverage: {coverage_percent(rows):.1f}%",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    try:
        cursor_dir = detect_cursor_dir(args.cursor_dir)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    try:
        db_path = find_cursor_db()
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    try:
        conn = get_connection(db_path)
    except Exception as exc:
        print(f"Error: Unable to open Cursor database: {exc}", file=sys.stderr)
        return 2

    try:
        conversations = get_recent_conversations(conn, args.project, args.sessions)
    finally:
        conn.close()

    if not conversations:
        if args.format == "json":
            print(
                json.dumps(
                    {
                        "sessions_analyzed": 0,
                        "failure_events": 0,
                        "message": "No matching conversations found.",
                    },
                    indent=2,
                )
            )
        else:
            print("Skill Gap Analysis\n==================\nNo matching conversations found.")
        return 0

    failure_by_domain = detect_failure_events(conversations)
    artifacts = load_knowledge_artifacts(cursor_dir)
    rows = compute_coverage(artifacts, failure_by_domain)
    total_events = sum(row["failures"] for row in rows)

    if args.format == "json":
        print(
            json.dumps(
                {
                    "sessions_analyzed": len(conversations),
                    "failure_events": total_events,
                    "coverage_summary": {
                        "domains_with_gaps": len([r for r in rows if r["coverage_count"] <= 1]),
                        "domains_well_covered": len(
                            [r for r in rows if r["coverage_count"] >= 2]
                        ),
                        "overall_coverage_percent": round(coverage_percent(rows), 1),
                    },
                    "domains": rows,
                },
                indent=2,
            )
        )
        return 0

    report = render_text_report(len(conversations), total_events, rows)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
