#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
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

_ALERTS_HEADER = "## Rootstock Alerts\n\n*Pending at session start — cleared after delivery*\n"
_ALERTS_SEPARATOR = "\n---\n\n"


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


def _get_graft_db_path() -> Path | None:
    """Resolve graft runtime DB path for current platform."""
    import os
    import platform

    system = platform.system()
    if system == "Windows":
        appdata = os.environ.get("APPDATA", "")
        if not appdata:
            return None
        return Path(appdata) / "rootstock" / "graft_runtime.db"

    if system == "Darwin":
        home = Path.home()
        return home / "Library" / "Application Support" / "rootstock" / "graft_runtime.db"

    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    if xdg_data_home:
        return Path(xdg_data_home) / "rootstock" / "graft_runtime.db"
    return Path.home() / ".local" / "share" / "rootstock" / "graft_runtime.db"


def _query_pending_notifications(db_path: Path) -> list[tuple[str, str, str, str, str]]:
    """Return pending (undelivered, unarchived) notifications as (id, severity, category, title, body) tuples.

    Returns empty list if table does not exist (old DB without migration applied yet).
    """
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.execute(
            """
            SELECT id, severity, category, title, body
            FROM notifications
            WHERE delivered_at IS NULL AND archived_at IS NULL
            ORDER BY
                CASE severity WHEN 'error' THEN 0 WHEN 'warning' THEN 1 ELSE 2 END,
                created_at ASC
            LIMIT 20
            """
        )
        return [(row[0], row[1], row[2], row[3], row[4]) for row in cursor.fetchall()]
    except Exception:
        # Table may not exist on old DBs — treat as empty
        return []
    finally:
        conn.close()


def _check_staleness_from_state(workspace_path: Path) -> list[tuple[str, str, str, str, str]]:
    """Hook-computed staleness check — works even if TrayRuntime hasn't written DB notifications.

    Reads .graft.state.json, returns a synthetic notification tuple if last_pull > 7 days.
    Handles both 'commit' and 'canonical_commit' key formats (backward compat).
    Returns list of (id, severity, category, title, body) — id is empty string for synthetic rows.
    """
    import time

    state_path = workspace_path / ".graft.state.json"
    if not state_path.exists():
        return []

    try:
        import json as _json

        data = _json.loads(state_path.read_text(encoding="utf-8"))
        last_pull = data.get("last_pull") or {}

        timestamp_str = last_pull.get("timestamp", "")
        if not timestamp_str:
            return []

        last_pull_secs = int(timestamp_str)
        now_secs = int(time.time())
        days_stale = (now_secs - last_pull_secs) // 86_400

        if days_stale < 7:
            return []

        title = f"Stale sync: {days_stale} days since last pull"
        body = (
            f"This project has not pulled from scion in {days_stale} days. "
            "Consider running Pull or Pull All from the Rootstock dashboard."
        )
        return [("", "warning", "sync", title, body)]
    except Exception:
        return []


def _mark_notifications_delivered(db_path: Path, ids: list[str]) -> None:
    """Mark the given notification IDs as delivered. Silently ignores empty list or missing table."""
    real_ids = [i for i in ids if i]  # filter out synthetic (empty-string) ids
    if not real_ids:
        return
    conn = sqlite3.connect(str(db_path))
    try:
        placeholders = ",".join("?" for _ in real_ids)
        conn.execute(
            f"UPDATE notifications SET delivered_at = datetime('now') WHERE id IN ({placeholders})",
            real_ids,
        )
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()


def _archive_old_notifications(db_path: Path, days: int = 7) -> None:
    """Archive delivered notifications older than `days` days. Best-effort; never raises."""
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            "UPDATE notifications SET archived_at = datetime('now') "
            "WHERE delivered_at IS NOT NULL AND archived_at IS NULL "
            "AND delivered_at < datetime('now', ?)",
            [f"-{days} days"],
        )
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()


def _format_alerts_prefix(rows: list[tuple[str, str, str, str, str]]) -> str:
    """Format notification rows as a markdown alerts section for prepending to 999 briefing.

    Returns empty string if rows is empty.
    """
    if not rows:
        return ""

    lines = [_ALERTS_HEADER, ""]
    for _id, severity, category, title, body in rows:
        lines.append(f"**[{severity} · {category}]** {title}")
        lines.append(body)
        lines.append("")

    lines.append("")
    return "\n".join(lines)


def _materialize_alerts(workspace_path: Path) -> str:
    """Query pending notifications + hook-computed staleness, format as alerts prefix.

    Marks DB rows delivered. Archives old rows. Returns the formatted prefix string
    (empty string if nothing to report). Never raises.
    """
    try:
        db_path = _get_graft_db_path()
        db_rows: list[tuple[str, str, str, str, str]] = []
        if db_path is not None:
            db_rows = _query_pending_notifications(db_path)

        staleness_rows = _check_staleness_from_state(workspace_path)

        # Deduplicate: if DB already has a staleness alert, skip hook-computed one
        has_sync_alert = any(r[2] == "sync" for r in db_rows)
        if has_sync_alert:
            staleness_rows = []

        all_rows = db_rows + staleness_rows

        if db_path is not None:
            delivered_ids = [r[0] for r in db_rows if r[0]]
            _mark_notifications_delivered(db_path, delivered_ids)
            _archive_old_notifications(db_path)

        return _format_alerts_prefix(all_rows)
    except Exception as exc:
        _log(f"[rootstock:alerts] error during alert materialization: {exc}")
        return ""


def main() -> int:
    """Bridge plain-text briefing output to Cursor hook JSON and persist as rule."""
    try:
        if not BRIEFING_SCRIPT.exists():
            _log(f"briefing script not found: {BRIEFING_SCRIPT}")
            alerts_prefix = _materialize_alerts(WORKSPACE_PATH)
            if alerts_prefix:
                _write_rule_file(alerts_prefix)
                _write_tool_copies(alerts_prefix)
            return 0

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
        except Exception as exc:
            _log(f"briefing subprocess failed: {exc}")
            alerts_prefix = _materialize_alerts(WORKSPACE_PATH)
            if alerts_prefix:
                _write_rule_file(alerts_prefix)
                _write_tool_copies(alerts_prefix)
            return 0

        alerts_prefix = _materialize_alerts(WORKSPACE_PATH)
        briefing_with_alerts = (
            alerts_prefix + _ALERTS_SEPARATOR + result.stdout if alerts_prefix else result.stdout
        )
        _write_rule_file(briefing_with_alerts)
        _write_tool_copies(briefing_with_alerts)
        _emit({})
        return 0
    except Exception as exc:  # pragma: no cover - hook must never block session creation
        _log(f"unexpected error: {exc}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
