#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = ["pyyaml>=6.0"]
# ///
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

AGENT_CHOICES = ("executor", "architect", "qa", "author", "curator", "researcher", "explorer")
VERIFY_TEMPLATES: dict[str, str] = {
    "executor": "Run lint and scoped tests for all touched files before returning. Verify no regressions.",
    "architect": "Provide design rationale for key decisions. Document trade-offs considered.",
    "qa": "Run full test suite for affected modules. Fix issues within scope. Escalate architectural concerns.",
    "author": "Verify prose accuracy against code. Check for stale references.",
    "curator": "Cite rubric criteria for each decision. Verify token budget compliance.",
    "researcher": "Cite sources for findings. Highlight confidence levels and open questions.",
    "explorer": "Map relevant code paths and dependencies. Surface unknowns before implementation.",
}
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "for",
    "from",
    "in",
    "into",
    "new",
    "of",
    "on",
    "or",
    "review",
    "the",
    "to",
    "with",
}
RISK_FIELDS = {
    "risk",
    "risk_score",
    "hotspot",
    "hotspot_score",
    "importance",
    "centrality",
    "churn",
    "complexity",
    "betweenness",
}


@dataclass(frozen=True)
class SkillMeta:
    name: str
    path: Path
    description: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a delegation brief skeleton with auto-gathered context.")
    parser.add_argument("-t", "--task", type=str, default=None, help="Task description. If omitted, reads stdin.")
    parser.add_argument("-a", "--agent", choices=AGENT_CHOICES, required=True, help="Target specialist agent type.")
    parser.add_argument("-f", "--files", nargs="*", default=None, help="Specific files expected to be touched.")
    parser.add_argument(
        "-w",
        "--workspace",
        type=Path,
        default=None,
        help="Workspace root (default: walk upward to find .cursor).",
    )
    return parser.parse_args(argv)


def detect_workspace(explicit: Path | None) -> tuple[Path, str]:
    if explicit is not None:
        resolved = explicit.expanduser().resolve()
        return resolved, "workspace provided by --workspace"
    current = Path.cwd().resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".cursor").is_dir():
            return candidate, "workspace auto-detected via .cursor"
    return current, "workspace fallback to current directory; .cursor not found in parent chain"


def resolve_task(task_arg: str | None) -> str:
    if task_arg and task_arg.strip():
        return task_arg.strip()
    if sys.stdin.isatty():
        raise ValueError("Task description required via --task/-t or stdin.")
    stdin_text = sys.stdin.read().strip()
    if not stdin_text:
        raise ValueError("Stdin was provided but empty. Pass --task/-t.")
    return stdin_text


def resolve_target_files(workspace: Path, raw_files: list[str] | None) -> tuple[list[Path], list[Path]]:
    if not raw_files:
        return [], []
    existing: list[Path] = []
    missing: list[Path] = []
    for item in raw_files:
        candidate = Path(item)
        resolved = candidate.resolve() if candidate.is_absolute() else (workspace / candidate).resolve()
        if resolved.exists():
            existing.append(resolved)
        else:
            missing.append(resolved)
    return existing, missing


def infer_candidate_files(task: str, workspace: Path, limit: int = 8) -> list[Path]:
    tokens = [t.lower() for t in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", task)]
    keywords = [t for t in tokens if t not in STOPWORDS]
    if not keywords:
        return []
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=workspace,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return []
    if result.returncode != 0:
        return []
    scored: list[tuple[int, str]] = []
    for raw in result.stdout.splitlines():
        lowered = raw.lower()
        score = sum(2 if f"/{kw}" in lowered or lowered.endswith(kw) else 1 for kw in keywords if kw in lowered)
        if score > 0:
            scored.append((score, raw))
    scored.sort(key=lambda item: (-item[0], len(item[1]), item[1]))
    return [(workspace / path_str).resolve() for _, path_str in scored[:limit]]


def parse_frontmatter(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    if not text.startswith("---"):
        return {}
    try:
        end_index = text.index("---", 3)
    except ValueError:
        return {}
    try:
        data = yaml.safe_load(text[3:end_index])
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def collect_skills(workspace: Path) -> list[SkillMeta]:
    skills_dir = workspace / ".cursor" / "skills"
    if not skills_dir.is_dir():
        return []
    skills: list[SkillMeta] = []
    for skill_dir in sorted(skills_dir.iterdir()):
        skill_file = skill_dir / "SKILL.md"
        if not skill_dir.is_dir() or not skill_file.exists():
            continue
        meta = parse_frontmatter(skill_file)
        name = str(meta.get("name") or skill_dir.name).strip()
        description = str(meta.get("description") or "").strip()
        if not description:
            continue
        skills.append(SkillMeta(name=name, path=skill_file, description=description))
    return skills


def match_skills(task: str, skills: list[SkillMeta], max_items: int = 6) -> list[SkillMeta]:
    task_tokens = {t.lower() for t in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", task) if t.lower() not in STOPWORDS}
    scored: list[tuple[int, SkillMeta]] = []
    for skill in skills:
        desc_tokens = set(re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", skill.description.lower()))
        overlap = len(task_tokens.intersection(desc_tokens))
        if overlap > 0:
            scored.append((overlap, skill))
    scored.sort(key=lambda item: (-item[0], item[1].name))
    return [skill for _, skill in scored[:max_items]]


def _extract_path_from_record(record: dict[str, Any]) -> str | None:
    keys = ("path", "file", "file_path", "filepath", "relative_path", "name")
    for key in keys:
        value = record.get(key)
        if isinstance(value, str) and ("/" in value or "\\" in value or "." in Path(value).name):
            return value
    return None


def _extract_risk_from_record(record: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in record.items() if k.lower() in RISK_FIELDS}


def _walk_json_records(node: Any, collector: list[dict[str, Any]]) -> None:
    if isinstance(node, dict):
        path_value = _extract_path_from_record(node)
        risk_values = _extract_risk_from_record(node)
        if path_value and risk_values:
            collector.append({"path": path_value, "risk": risk_values})
        for value in node.values():
            _walk_json_records(value, collector)
        return
    if isinstance(node, list):
        for item in node:
            _walk_json_records(item, collector)


def collect_cache_risk_signals(workspace: Path, target_files: list[Path]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    notes: list[str] = []
    cache_path = workspace / ".cursor" / ".codebase-sense" / "cache.db"
    if not cache_path.exists():
        notes.append("Codebase-sense cache unavailable.")
        return {}, notes
    target_rel = {(str(path.relative_to(workspace)).replace("\\", "/"), path) for path in target_files if path.is_absolute()}
    risk_by_file: dict[str, dict[str, Any]] = {}
    try:
        with sqlite3.connect(cache_path) as conn:
            rows = conn.execute("SELECT key, value FROM scan_meta").fetchall()
    except sqlite3.Error as exc:
        notes.append(f"Codebase-sense cache read failed: {exc}.")
        return {}, notes
    for key, value in rows:
        if not isinstance(value, str):
            continue
        try:
            payload = json.loads(value)
        except json.JSONDecodeError:
            continue
        extracted: list[dict[str, Any]] = []
        _walk_json_records(payload, extracted)
        for record in extracted:
            raw_path = str(record["path"]).replace("\\", "/")
            for target_str, target_path in target_rel:
                if raw_path.endswith(target_str):
                    relative_key = str(target_path.relative_to(workspace)).replace("\\", "/")
                    merged = dict(risk_by_file.get(relative_key, {}))
                    merged.update(record["risk"])
                    merged["source"] = key
                    risk_by_file[relative_key] = merged
    if not risk_by_file:
        notes.append("No file-level risk indicators matched target files in cache.")
    return risk_by_file, notes


def collect_recent_changes(workspace: Path, files: list[Path]) -> tuple[list[str], str | None]:
    cmd = ["git", "log", "--oneline", "-5"]
    if files:
        cmd.extend(["--", *[str(path.relative_to(workspace)) for path in files if path.exists()]])
    try:
        result = subprocess.run(cmd, cwd=workspace, capture_output=True, text=True, check=False)
    except OSError as exc:
        return [], f"git invocation failed: {exc}"
    if result.returncode != 0:
        stderr = result.stderr.strip() or f"git exited {result.returncode}"
        return [], stderr
    entries = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return entries, None


def format_path(path: Path, workspace: Path) -> str:
    try:
        return str(path.relative_to(workspace)).replace("\\", "/")
    except ValueError:
        return str(path)


def build_markdown(
    task: str,
    agent: str,
    workspace: Path,
    workspace_note: str,
    target_files: list[Path],
    missing_files: list[Path],
    inferred_files: list[Path],
    risk_signals: dict[str, dict[str, Any]],
    risk_notes: list[str],
    recent_changes: list[str],
    recent_error: str | None,
    matched_skills: list[SkillMeta],
) -> str:
    effective_files = target_files if target_files else inferred_files
    lines: list[str] = [f"## Task: {task}", "", "### Context"]
    lines.append(f"- Workspace: `{workspace}` ({workspace_note})")
    lines.append(f"- Target agent: `{agent}`")
    if target_files:
        lines.append("- Scope source: explicit `--files` list")
    elif inferred_files:
        lines.append("- Scope source: inferred from task keywords over tracked files")
    else:
        lines.append("- Scope source: no file candidates resolved; orchestrator should define writable scope")
    if risk_notes:
        for note in risk_notes:
            lines.append(f"- Risk data note: {note}")
    lines.extend(["", "### Target Files"])
    if effective_files:
        for path in effective_files:
            relative = format_path(path, workspace)
            exists_label = "exists" if path.exists() else "missing"
            risk = risk_signals.get(relative, {})
            risk_fields = ", ".join(f"{k}={v}" for k, v in risk.items() if k != "source")
            if risk_fields:
                lines.append(f"- `{relative}` ({exists_label}) — {risk_fields}")
            else:
                lines.append(f"- `{relative}` ({exists_label})")
    else:
        lines.append("- No candidate files identified from task text.")
    for missing in missing_files:
        lines.append(f"- `{format_path(missing, workspace)}` (missing)")
    lines.extend(["", "### Recent Changes"])
    if recent_changes:
        for entry in recent_changes:
            lines.append(f"- {entry}")
    elif recent_error:
        lines.append(f"- Unavailable: {recent_error}")
    else:
        lines.append("- No commits found for current scope.")
    lines.extend(["", "### Applicable Constraints"])
    lines.append("- NASA-grade implementation discipline: guard clauses, shallow nesting, single success path.")
    if matched_skills:
        for skill in matched_skills:
            lines.append(f"- `{skill.name}`: {skill.description}")
    else:
        lines.append("- No strongly matched skills from task keywords; review `.cursor/skills` manually.")
    lines.extend(["", "### Verification Criteria"])
    lines.append(f"- {VERIFY_TEMPLATES[agent]}")
    lines.extend(["", "### Writable File Set"])
    if effective_files:
        for path in effective_files:
            lines.append(f"- `{format_path(path, workspace)}`")
    else:
        lines.append("- Define writable file set before execution.")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    print(
        "DEPRECATED: Use query-cascade.py for pre-dispatch intelligence. See codebase-sense skill.",
        file=sys.stderr,
    )
    args = parse_args(argv)
    try:
        task = resolve_task(args.task)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    workspace, workspace_note = detect_workspace(args.workspace)
    target_files, missing_files = resolve_target_files(workspace, args.files)
    inferred_files = infer_candidate_files(task, workspace) if not target_files else []
    all_context_files = target_files or inferred_files
    risk_signals: dict[str, dict[str, Any]] = {}
    risk_notes: list[str] = []
    try:
        risk_signals, risk_notes = collect_cache_risk_signals(workspace, all_context_files)
    except Exception as exc:
        risk_notes = [f"Codebase-sense cache probe failed: {exc}."]
    try:
        recent_changes, recent_error = collect_recent_changes(workspace, all_context_files)
    except Exception as exc:
        recent_changes, recent_error = [], f"recent change lookup failed: {exc}"
    try:
        skills = collect_skills(workspace)
        matched_skills = match_skills(task, skills)
    except Exception as exc:
        matched_skills = []
        risk_notes.append(f"Skills scan failed: {exc}.")
    output = build_markdown(
        task=task,
        agent=args.agent,
        workspace=workspace,
        workspace_note=workspace_note,
        target_files=target_files,
        missing_files=missing_files,
        inferred_files=inferred_files,
        risk_signals=risk_signals,
        risk_notes=risk_notes,
        recent_changes=recent_changes,
        recent_error=recent_error,
        matched_skills=matched_skills,
    )
    print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
