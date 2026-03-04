from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXCLUDED_PREFIXES = (
    ".cursor/",
    ".claude/",
    ".aiassistant/",
    "node_modules/",
    "target/",
    "build/",
    "dist/",
    ".git/",
)

STATUS_TO_ACTION = {
    "A": "add",
    "M": "modify",
    "D": "delete",
    "R": "rename",
    "C": "copy",
    "T": "type_change",
    "U": "unmerged",
}


def _normalize_repo_path(repo_name: str, raw_path: str) -> str:
    normalized = raw_path.replace("\\", "/").lstrip("./")
    if normalized.startswith(".cursor/"):
        normalized = normalized[1:]
    if not normalized.startswith(f"{repo_name}/"):
        normalized = f"{repo_name}/{normalized}"
    return normalized


def _is_excluded_path(path: str) -> bool:
    normalized = path.replace("\\", "/").lstrip("./")
    return any(normalized.startswith(prefix.lstrip("./")) for prefix in EXCLUDED_PREFIXES)


def _run_git_log(repo_path: Path, days: int) -> str:
    command = [
        "git",
        "log",
        f"--since={int(days)} days ago",
        "--pretty=format:%H|%aI|%an|%s",
        "--name-status",
    ]
    result = subprocess.run(
        command,
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout


def collect_git_events(repo_path: Path, days: int = 14, verbose: bool = False) -> list[dict[str, Any]]:
    if not repo_path.exists():
        return []
    if not (repo_path / ".git").exists():
        return []

    repo_name = repo_path.name
    output = _run_git_log(repo_path, days)
    if not output.strip():
        return []

    events: list[dict[str, Any]] = []
    current_commit: dict[str, str] | None = None
    knowledge_time = datetime.now(timezone.utc).isoformat()

    for raw_line in output.splitlines():
        line = raw_line.rstrip()
        if not line:
            continue

        if "|" in line:
            parts = line.split("|", 3)
            if len(parts) == 4 and len(parts[0]) >= 7:
                current_commit = {
                    "hash": parts[0].strip(),
                    "timestamp": parts[1].strip(),
                    "author": parts[2].strip(),
                    "subject": parts[3].strip(),
                }
                continue

        if current_commit is None:
            continue

        status_parts = line.split("\t")
        if len(status_parts) < 2:
            continue

        raw_status = status_parts[0].strip()
        status_code = raw_status[:1]
        path_for_event = ""
        if status_code in {"R", "C"} and len(status_parts) >= 3:
            path_for_event = status_parts[2].strip()
        else:
            path_for_event = status_parts[1].strip()

        if not path_for_event:
            continue
        if _is_excluded_path(path_for_event):
            continue

        artifact_key = _normalize_repo_path(repo_name, path_for_event)
        if not artifact_key:
            continue

        event_id = f"git:{repo_name}:{current_commit['hash']}:{artifact_key}"
        event = {
            "id": event_id,
            "event_time": current_commit["timestamp"],
            "knowledge_time": knowledge_time,
            "strand_id": "main",
            "session_id": None,
            "attempt_id": None,
            "event_type": "git_commit",
            "action": STATUS_TO_ACTION.get(status_code, "modify"),
            "artifact_key": artifact_key,
            "status": "success",
            "payload_json": {
                "repo": repo_name,
                "commit_hash": current_commit["hash"],
                "author": current_commit["author"],
                "message_summary": current_commit["subject"],
                "status_code": status_code,
            },
            "causal_antecedent_id": None,
            "causal_type": None,
            "revelation": None,
            "episode_character": None,
            "coherence_signal": None,
            "confidence": 1.0,
            "source_ref": f"git:{current_commit['hash']}",
        }
        events.append(event)

    events.sort(key=lambda event: (event["event_time"], event["id"]))
    if verbose:
        print(f"[git_analyzer] {repo_name}: {len(events)} events")
    return events


def collect_workspace_git_events(
    workspace_path: Path,
    days: int = 14,
    verbose: bool = False,
) -> list[dict[str, Any]]:
    workspace = workspace_path.resolve()
    all_events = collect_git_events(workspace, days=days, verbose=verbose)
    all_events.sort(key=lambda event: (event["event_time"], event["id"]))
    return all_events


def dump_git_events_json(events: list[dict[str, Any]]) -> str:
    return json.dumps(events, ensure_ascii=True, indent=2)

