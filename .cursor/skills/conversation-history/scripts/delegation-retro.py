#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Analyze delegation outcomes from Cursor conversation history.

This analysis is heuristic. It infers delegation events, brief quality signals,
and outcomes from pattern matching over message text rather than semantic
understanding of conversation intent.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from db_utils import (
    extract_conversations,
    get_conversation_date,
    get_cursor_db_path,
    is_project_conversation,
    load_database,
)

AGENT_TYPES = (
    "the-executor",
    "the-architect",
    "the-qa-tester",
    "the-author",
    "the-curator",
    "explore",
    "shell",
)

TASK_MARKERS = (
    "## task:",
    "### context",
    "### verification",
    "### files",
    "subagent_type",
    "delegation",
    "dispatch",
    "handoff",
    "task tool",
    "subagent",
)

SUCCESS_MARKERS = (
    "completed",
    "done",
    "implemented",
    "finished",
    "verified",
    "passes",
    "all checks pass",
)

REWORK_MARKERS = (
    "fix",
    "adjust",
    "correction",
    "rework",
    "retry",
    "try again",
    "missing",
    "not quite",
    "still failing",
    "follow-up",
    "redispatch",
)

FAILURE_MARKERS = (
    "error",
    "failed",
    "exception",
    "traceback",
    "cannot proceed",
    "abandon",
    "blocked",
    "timeout",
)

RISK_MARKERS = (
    "risk",
    "warning",
    "blast radius",
    "cascade",
    "cross-file",
    "dependency",
    "guard",
    "fallback",
)

SKILL_RULE_MARKERS = (
    "skill",
    "skills/",
    "rule",
    "rules/",
    "skILL.md".lower(),
    "rule.mdc",
)

VERIFICATION_MARKERS = ("verify", "test", "lint", "build", "check", "validation")
FILE_PATH_PATTERN = re.compile(r"`[^`\n]+\.[a-z0-9_]+`", re.IGNORECASE)
TRIGGER_PHRASES = {
    "Missing test files in WFS": ("missing test", "test file", "wfs"),
    "Incomplete verification criteria": ("incomplete verification", "missing verification", "no tests"),
    "Cross-file dependencies not mentioned": ("cross-file", "dependency", "dependent file"),
    "Unclear acceptance criteria": ("unclear", "ambiguous", "acceptance"),
    "Re-dispatch after failed first pass": ("redispatch", "re-dispatch", "retry"),
}


@dataclass(frozen=True)
class ConversationRecord:
    conversation_id: str
    messages: list[dict[str, Any]]
    timestamp: Any


@dataclass(frozen=True)
class DelegationEvent:
    conversation_id: str
    message_index: int
    agent_type: str
    brief_text: str
    outcome: str
    outcome_reason: str
    has_verification: bool
    has_file_paths: bool
    has_risk_warning: bool
    has_skill_reference: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze delegation quality and outcomes from Cursor conversations."
    )
    parser.add_argument(
        "--project",
        "-p",
        help="Filter to conversations about a specific project path (optional).",
    )
    parser.add_argument(
        "--sessions",
        "-n",
        type=int,
        default=30,
        help="Number of recent sessions to analyze (default: 30).",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text).",
    )
    args = parser.parse_args()
    if args.sessions < 1:
        parser.error("--sessions must be >= 1")
    return args


def _extract_message_text(message: dict[str, Any]) -> str:
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
    return "\n".join(parts)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _detect_agent_type(text_lower: str) -> str | None:
    for agent_type in AGENT_TYPES:
        if agent_type in text_lower:
            return agent_type
    if "explorer" in text_lower:
        return "explore"
    return None


def _is_delegation_candidate(text: str) -> bool:
    text_lower = _normalize(text)
    if not text_lower:
        return False
    has_agent = _detect_agent_type(text_lower) is not None
    has_task_marker = _contains_any(text_lower, TASK_MARKERS)
    return has_agent and has_task_marker


def _classify_outcome(window_text: str, remaining_text: str) -> tuple[str, str]:
    window_lower = _normalize(window_text)
    remaining_lower = _normalize(remaining_text)
    if _contains_any(window_lower, FAILURE_MARKERS):
        return ("failure", "failure markers in follow-up")
    if _contains_any(window_lower, REWORK_MARKERS):
        return ("rework", "rework/correction markers in follow-up")
    if _contains_any(remaining_lower, REWORK_MARKERS) and "fix" in remaining_lower:
        return ("rework", "later fix request detected")
    if _contains_any(window_lower, SUCCESS_MARKERS):
        return ("success", "completion markers in follow-up")
    return ("success", "no negative markers detected")


def _quality_signals(brief_text: str) -> tuple[bool, bool, bool, bool]:
    lowered = _normalize(brief_text)
    has_verification = _contains_any(lowered, VERIFICATION_MARKERS) or "### verification" in lowered
    has_file_paths = bool(FILE_PATH_PATTERN.search(brief_text)) or "### files" in lowered
    has_risk_warning = _contains_any(lowered, RISK_MARKERS)
    has_skill_reference = _contains_any(lowered, SKILL_RULE_MARKERS)
    return (has_verification, has_file_paths, has_risk_warning, has_skill_reference)


def _sorted_conversations(
    all_conversations: dict[str, list[dict[str, Any]]],
    project_path: str | None,
    limit: int,
) -> list[ConversationRecord]:
    records: list[ConversationRecord] = []
    for conv_id, messages in all_conversations.items():
        if project_path and not is_project_conversation(messages, project_path):
            continue
        timestamp = get_conversation_date(messages)
        records.append(
            ConversationRecord(
                conversation_id=conv_id,
                messages=messages,
                timestamp=timestamp,
            )
        )
    records.sort(key=lambda rec: rec.timestamp or 0, reverse=True)
    return records[:limit]


def _extract_delegation_events(conversations: list[ConversationRecord]) -> list[DelegationEvent]:
    events: list[DelegationEvent] = []
    for conversation in conversations:
        message_texts = [_extract_message_text(msg) for msg in conversation.messages]
        for index, text in enumerate(message_texts):
            if not _is_delegation_candidate(text):
                continue
            lowered = _normalize(text)
            agent_type = _detect_agent_type(lowered)
            if not agent_type:
                continue
            window = " ".join(message_texts[index + 1 : index + 7])
            remaining = " ".join(message_texts[index + 1 :])
            outcome, outcome_reason = _classify_outcome(window, remaining)
            has_verification, has_file_paths, has_risk_warning, has_skill_reference = _quality_signals(
                text
            )
            events.append(
                DelegationEvent(
                    conversation_id=conversation.conversation_id,
                    message_index=index,
                    agent_type=agent_type,
                    brief_text=text,
                    outcome=outcome,
                    outcome_reason=outcome_reason,
                    has_verification=has_verification,
                    has_file_paths=has_file_paths,
                    has_risk_warning=has_risk_warning,
                    has_skill_reference=has_skill_reference,
                )
            )
    return events


def _parse_agent_catalog(workspace_root: Path) -> list[tuple[str, str]]:
    catalog_path = workspace_root / ".cursor" / "handoffs" / "agent-catalog.md"
    if not catalog_path.exists():
        return []
    try:
        text = catalog_path.read_text(encoding="utf-8")
    except OSError:
        return []

    lines = [line.strip().lower() for line in text.splitlines() if line.strip()]
    rows: list[tuple[str, str]] = []
    for line in lines:
        agent_type = _detect_agent_type(line)
        if not agent_type:
            continue
        if _contains_any(line, FAILURE_MARKERS):
            rows.append((agent_type, "failure"))
            continue
        if _contains_any(line, REWORK_MARKERS):
            rows.append((agent_type, "rework"))
            continue
        if _contains_any(line, SUCCESS_MARKERS):
            rows.append((agent_type, "success"))
            continue
    return rows


def _percent(part: int, whole: int) -> float:
    if whole < 1:
        return 0.0
    return round((part / whole) * 100, 1)


def _format_quality_signal(events: list[DelegationEvent], field: str) -> dict[str, float]:
    with_signal = [event for event in events if getattr(event, field)]
    without_signal = [event for event in events if not getattr(event, field)]
    with_clean = sum(1 for event in with_signal if event.outcome == "success")
    without_clean = sum(1 for event in without_signal if event.outcome == "success")
    return {
        "with_share_pct": _percent(len(with_signal), len(events)),
        "with_clean_pct": _percent(with_clean, len(with_signal)),
        "without_share_pct": _percent(len(without_signal), len(events)),
        "without_clean_pct": _percent(without_clean, len(without_signal)),
    }


def _top_rework_triggers(events: list[DelegationEvent]) -> list[tuple[str, int]]:
    trigger_counts: Counter[str] = Counter()
    rework_events = [event for event in events if event.outcome in {"rework", "failure"}]
    for event in rework_events:
        brief_lower = _normalize(event.brief_text)
        if not event.has_verification:
            trigger_counts["Incomplete verification criteria"] += 1
        if not event.has_file_paths:
            trigger_counts["Missing file references"] += 1
        if not event.has_risk_warning:
            trigger_counts["No risk/cascade warning"] += 1
        for label, markers in TRIGGER_PHRASES.items():
            if any(marker in brief_lower for marker in markers):
                trigger_counts[label] += 1
    return trigger_counts.most_common(3)


def _summarize(
    events: list[DelegationEvent],
    catalog_rows: list[tuple[str, str]],
) -> dict[str, Any]:
    by_agent: dict[str, dict[str, int]] = defaultdict(lambda: {"success": 0, "rework": 0, "failure": 0})
    for event in events:
        by_agent[event.agent_type][event.outcome] += 1
    for agent_type, status in catalog_rows:
        if status not in by_agent[agent_type]:
            continue
        by_agent[agent_type][status] += 1

    quality = {
        "verification": _format_quality_signal(events, "has_verification"),
        "file_paths": _format_quality_signal(events, "has_file_paths"),
        "risk_warnings": _format_quality_signal(events, "has_risk_warning"),
        "skill_references": _format_quality_signal(events, "has_skill_reference"),
    }
    return {
        "delegations_found": len(events),
        "by_agent_type": by_agent,
        "quality_signals": quality,
        "top_rework_triggers": _top_rework_triggers(events),
        "catalog_rows_used": len(catalog_rows),
    }


def _recommendations(summary: dict[str, Any]) -> list[str]:
    quality = summary["quality_signals"]
    recommendations: list[str] = []
    for key, label in (
        ("verification", "verification criteria"),
        ("file_paths", "file paths"),
        ("risk_warnings", "risk warnings"),
        ("skill_references", "skill/rule references"),
    ):
        with_clean = quality[key]["with_clean_pct"]
        without_clean = quality[key]["without_clean_pct"]
        delta = round(with_clean - without_clean, 1)
        if delta <= 0:
            continue
        recommendations.append(
            f"Always include {label} in briefs (correlation: +{delta}% clean delivery)"
        )
    if recommendations:
        return recommendations[:3]
    return ["No strong positive brief-signal correlations found in this sample."]


def _render_text_report(sessions_count: int, summary: dict[str, Any], recommendations: list[str]) -> str:
    lines = [
        "Delegation Retrospective",
        "=========================",
        f"Sessions analyzed: {sessions_count}",
        f"Delegations found: {summary['delegations_found']}",
        "",
        "By Agent Type:",
    ]
    by_agent = summary["by_agent_type"]
    if not by_agent:
        lines.append("  No delegation events detected.")
    else:
        for agent_type in sorted(by_agent.keys()):
            counts = by_agent[agent_type]
            total = counts["success"] + counts["rework"] + counts["failure"]
            clean_pct = _percent(counts["success"], total)
            rework_pct = _percent(counts["rework"], total)
            fail_pct = _percent(counts["failure"], total)
            lines.append(
                f"  {agent_type}: {total} delegations | {clean_pct:.1f}% clean | "
                f"{rework_pct:.1f}% rework | {fail_pct:.1f}% failed"
            )

    quality = summary["quality_signals"]
    lines.extend(
        [
            "",
            "Brief Quality Signals:",
            "  Briefs with verification criteria: "
            f"{quality['verification']['with_share_pct']:.1f}% -> "
            f"{quality['verification']['with_clean_pct']:.1f}% clean delivery",
            "  Briefs without verification criteria: "
            f"{quality['verification']['without_share_pct']:.1f}% -> "
            f"{quality['verification']['without_clean_pct']:.1f}% clean delivery",
            "  Briefs with file paths: "
            f"{quality['file_paths']['with_share_pct']:.1f}% -> "
            f"{quality['file_paths']['with_clean_pct']:.1f}% clean delivery",
            "  Briefs with risk warnings: "
            f"{quality['risk_warnings']['with_share_pct']:.1f}% -> "
            f"{quality['risk_warnings']['with_clean_pct']:.1f}% clean delivery",
            "  Briefs referencing skills/rules: "
            f"{quality['skill_references']['with_share_pct']:.1f}% -> "
            f"{quality['skill_references']['with_clean_pct']:.1f}% clean delivery",
            "",
            "Top Rework Triggers:",
        ]
    )
    triggers = summary["top_rework_triggers"]
    if not triggers:
        lines.append("  1. No significant rework triggers in this sample")
    else:
        for index, (trigger, count) in enumerate(triggers, start=1):
            lines.append(f"  {index}. {trigger} ({count} occurrences)")

    lines.extend(["", "Recommendations:"])
    for recommendation in recommendations:
        lines.append(f"  - {recommendation}")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()

    db_path = get_cursor_db_path()
    if not db_path:
        print("Error: Cursor database path could not be detected.", file=sys.stderr)
        return 2

    try:
        conn = load_database(db_path)
    except Exception as exc:
        print(f"Error: Unable to open Cursor database: {exc}", file=sys.stderr)
        return 2

    try:
        all_conversations = extract_conversations(conn)
    finally:
        conn.close()

    conversation_records = _sorted_conversations(all_conversations, args.project, args.sessions)
    if not conversation_records:
        if args.format == "json":
            print(
                json.dumps(
                    {
                        "sessions_analyzed": 0,
                        "delegations_found": 0,
                        "message": "No matching conversations found.",
                    },
                    indent=2,
                )
            )
        else:
            print("Delegation Retrospective\n=========================\nNo matching conversations found.")
        return 0

    events = _extract_delegation_events(conversation_records)
    if not events:
        payload = {
            "sessions_analyzed": len(conversation_records),
            "delegations_found": 0,
            "message": "No delegations found in the analyzed sessions.",
        }
        if args.format == "json":
            print(json.dumps(payload, indent=2))
        else:
            print(
                "Delegation Retrospective\n"
                "=========================\n"
                f"Sessions analyzed: {len(conversation_records)}\n"
                "No delegations found in the analyzed sessions."
            )
        return 0

    workspace_root = Path(__file__).resolve().parents[4]
    catalog_rows = _parse_agent_catalog(workspace_root)
    summary = _summarize(events, catalog_rows)
    recommendations = _recommendations(summary)

    if args.format == "json":
        by_agent_json: dict[str, dict[str, float]] = {}
        for agent_type, counts in summary["by_agent_type"].items():
            total = counts["success"] + counts["rework"] + counts["failure"]
            by_agent_json[agent_type] = {
                "delegations": total,
                "clean_pct": _percent(counts["success"], total),
                "rework_pct": _percent(counts["rework"], total),
                "failed_pct": _percent(counts["failure"], total),
            }
        print(
            json.dumps(
                {
                    "sessions_analyzed": len(conversation_records),
                    "delegations_found": summary["delegations_found"],
                    "catalog_rows_used": summary["catalog_rows_used"],
                    "by_agent_type": by_agent_json,
                    "brief_quality_signals": summary["quality_signals"],
                    "top_rework_triggers": [
                        {"trigger": trigger, "occurrences": count}
                        for trigger, count in summary["top_rework_triggers"]
                    ],
                    "recommendations": recommendations,
                    "heuristic_notice": (
                        "Pattern-matching heuristic analysis; not semantic intent understanding."
                    ),
                },
                indent=2,
            )
        )
        return 0

    report = _render_text_report(len(conversation_records), summary, recommendations)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
