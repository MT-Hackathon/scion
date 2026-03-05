#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
from __future__ import annotations

import json
import os
import platform
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


def _normalize_workspace_root(raw: str) -> Path:
    """Normalize workspace root for Windows (e.g. /c:/Users/... -> c:/Users/...)."""
    s = raw.strip()
    if len(s) >= 3 and s[0] == "/" and s[2] == ":":
        s = s[1:]
    return Path(s).resolve()


def _resolve_paths_from_stdin() -> tuple[Path, Path, Path, Path, list[Path]] | None:
    """Parse hook payload from stdin; return (workspace_path, briefing_script, rule_dir, rule_path, repo_roots) or None for fallback."""
    try:
        raw = sys.stdin.read()
        brace = raw.find("{")
        if brace > 0:
            raw = raw[brace:]
        if not raw.strip():
            return None
        payload = json.loads(raw)
        roots = payload.get("workspace_roots") or []
        if not roots:
            return None
        project_root = _normalize_workspace_root(roots[0])
        workspace_path = project_root
        briefing_script = project_root / ".cursor" / "skills" / "codebase-sense" / "scripts" / "briefing.py"
        rule_dir = project_root / ".cursor" / "rules" / "999-codebase-briefing"
        rule_path = rule_dir / "RULE.mdc"
        repo_roots = [_normalize_workspace_root(r) for r in roots]
        return (workspace_path, briefing_script, rule_dir, rule_path, repo_roots)
    except (json.JSONDecodeError, IndexError, OSError):
        return None


def _resolve_paths_from_file() -> tuple[Path, Path, Path, Path, list[Path]]:
    """Fallback: resolve paths from this script's location (project .cursor/hooks/)."""
    base = Path(__file__).resolve().parents[1]
    workspace_path = Path(__file__).resolve().parents[2]
    briefing_script = base / "skills" / "codebase-sense" / "scripts" / "briefing.py"
    rule_dir = base / "rules" / "999-codebase-briefing"
    rule_path = rule_dir / "RULE.mdc"
    repo_roots = [workspace_path]
    return (workspace_path, briefing_script, rule_dir, rule_path, repo_roots)


_resolved = _resolve_paths_from_stdin()
if _resolved is not None:
    WORKSPACE_PATH, BRIEFING_SCRIPT, RULE_DIR, RULE_PATH, _REPO_ROOTS = _resolved
    _PATH_SOURCE = "payload"
else:
    WORKSPACE_PATH, BRIEFING_SCRIPT, RULE_DIR, RULE_PATH, _REPO_ROOTS = _resolve_paths_from_file()
    _PATH_SOURCE = "__file__"

RULE_FRONTMATTER = """\
---
alwaysApply: true
---

"""

_REPLICATION_TARGETS: list[tuple[str, ...]] = [
    (".aiassistant", "rules", "codebase-briefing.md"),
    (".claude", "rules", "codebase-briefing.md"),
]


def _log(message: str) -> None:
    """Write diagnostic message to stderr (visible in Cursor Hooks output panel)."""
    print(f"[session_briefing] {message}", file=sys.stderr, flush=True)


def _emit(payload: dict[str, Any]) -> None:
    """Write hook response JSON to stdout."""
    json.dump(payload, sys.stdout)
    sys.stdout.write("\n")
    sys.stdout.flush()


def _write_rule_file(briefing_text: str) -> None:
    """Write briefing as an always-applied Cursor rule (.mdc)."""
    try:
        RULE_DIR.mkdir(parents=True, exist_ok=True)
        RULE_PATH.write_text(RULE_FRONTMATTER + briefing_text, encoding="utf-8")
    except Exception as exc:
        _log(f"failed to write rule file: {exc}")


def _write_tool_copies(briefing_text: str) -> None:
    """Replicate codebase-sense briefing to each repo's tool-specific rules directories.

    Targets: .aiassistant/rules/ (JetBrains), .claude/rules/ (Claude Code).
    Best-effort; log failures, never block.
    """
    for repo_root in _REPO_ROOTS:
        for target_parts in _REPLICATION_TARGETS:
            target = repo_root / Path(*target_parts)
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(briefing_text, encoding="utf-8")
            except Exception as exc:
                _log(f"Could not write codebase-briefing to {target}: {exc}")


_MEMORY_START = "<!-- ROOTSTOCK:MEMORY:START -->"
_MEMORY_END = "<!-- ROOTSTOCK:MEMORY:END -->"


def _get_graft_db_path() -> Path | None:
    """Locate graft_runtime.db in the platform-appropriate app data directory."""
    system = platform.system()
    if system == "Windows":
        base = os.environ.get("APPDATA", "")
    elif system == "Darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME", "") or os.path.expanduser("~/.local/share")
    if not base:
        return None
    db_path = Path(base) / "rootstock" / "graft_runtime.db"
    return db_path if db_path.exists() else None


def _query_memories(db_path: Path) -> list[tuple[str, str, str | None]]:
    """Return top-ranked active memories as (memory_kind, claim, project_id) tuples."""
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.execute(
            """
            SELECT memory_kind, claim, project_id
            FROM memories
            WHERE status = 'active'
              AND supersedes_id IS NULL
            ORDER BY (activation_base * 0.7 + evidence_count * 0.3) DESC
            LIMIT 10
            """
        )
        return [(row[0], row[1], row[2]) for row in cursor.fetchall()]
    finally:
        conn.close()


def _format_memory_section(rows: list[tuple[str, str, str | None]]) -> str:
    """Build the full ROOTSTOCK:MEMORY block string from queried rows."""
    if not rows:
        return (
            f"{_MEMORY_START}\n"
            "*No memories yet — use write_memory via Rootstock MCP to record decisions and learnings.*\n"
            f"{_MEMORY_END}"
        )
    lines: list[str] = [
        _MEMORY_START,
        "*Operational memory from graft_runtime.db — refreshed each session*",
        "",
    ]
    for memory_kind, claim, project_id in rows:
        entry = f"**[{memory_kind}]** {claim}"
        if project_id:
            entry += f" *({project_id})*"
        lines.append(entry)
    lines.append("")
    lines.append(_MEMORY_END)
    return "\n".join(lines)


def _update_memory_rule(workspace_path: Path, new_section: str) -> None:
    """Atomically replace the operational memory block in 998-temporal-self/RULE.mdc."""
    rule_path = workspace_path / ".cursor" / "rules" / "998-temporal-self" / "RULE.mdc"
    if not rule_path.exists():
        _log("[rootstock:memory] 998-temporal-self/RULE.mdc not found, skipping")
        return

    content = rule_path.read_text(encoding="utf-8")
    start_idx = content.find(_MEMORY_START)
    end_idx = content.find(_MEMORY_END)

    if start_idx == -1 or end_idx == -1:
        _log("[rootstock:memory] memory markers not found in RULE.mdc, skipping")
        return

    end_idx += len(_MEMORY_END)
    updated = content[:start_idx] + new_section + content[end_idx:]

    tmp_fd, tmp_path = tempfile.mkstemp(dir=rule_path.parent, suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
            fh.write(updated)
        os.replace(tmp_path, rule_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _materialize_memories(workspace_path: Path) -> None:
    """Query graft_runtime.db and write operational memories into the 998 rule file."""
    try:
        db_path = _get_graft_db_path()
        if db_path is None:
            _log("[rootstock:memory] graft_runtime.db not found, writing empty section")
            rows: list[tuple[str, str, str | None]] = []
        else:
            rows = _query_memories(db_path)
        section = _format_memory_section(rows)
        _update_memory_rule(workspace_path, section)
    except Exception as exc:
        _log(f"[rootstock:memory] error during memory materialization: {exc}")


def main() -> int:
    """Bridge plain-text briefing output to Cursor hook JSON and persist as rule."""
    try:
        if not BRIEFING_SCRIPT.exists():
            _log(f"briefing script not found: {BRIEFING_SCRIPT}")
        else:
            try:
                result = subprocess.run(
                    [
                        "uv",
                        "run",
                        str(BRIEFING_SCRIPT),
                        str(WORKSPACE_PATH),
                        "--this-repo-only",
                        "--max-lines",
                        "120",
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                _write_rule_file(result.stdout)
                _write_tool_copies(result.stdout)
            except Exception as exc:
                _log(f"briefing subprocess failed: {exc}")

        _materialize_memories(WORKSPACE_PATH)
        _emit({})
        return 0
    except Exception as exc:  # pragma: no cover - hook must never block session creation
        _log(f"unexpected error: {exc}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
