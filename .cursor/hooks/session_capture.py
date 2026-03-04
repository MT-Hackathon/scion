#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "temporal-self"
    / "scripts"
)


def _resolve_workspace_path() -> Path:
    file_path = globals().get("__file__")
    if file_path:
        return Path(file_path).resolve().parents[2]
    return Path.cwd()


WORKSPACE_PATH = _resolve_workspace_path()


def _log(message: str) -> None:
    print(f"[session_capture] {message}", file=sys.stderr, flush=True)


def _emit(payload: dict[str, Any]) -> None:
    json.dump(payload, sys.stdout)
    sys.stdout.write("\n")
    sys.stdout.flush()


def _find_transcripts_dir() -> Path | None:
    cursor_projects = Path.home() / ".cursor" / "projects"
    if not cursor_projects.exists():
        return None
    workspace_str = str(WORKSPACE_PATH).replace("\\", "-").replace("/", "-").replace(":", "")
    for project_dir in cursor_projects.iterdir():
        transcripts = project_dir / "agent-transcripts"
        if transcripts.is_dir():
            if workspace_str.lower() in project_dir.name.lower() or project_dir.name.lower() in workspace_str.lower():
                return transcripts
    return None


def _run_script(script_name: str, extra_args: list[str] | None = None) -> bool:
    script_path = SCRIPTS_DIR / script_name
    if not script_path.exists():
        _log(f"script not found: {script_path}")
        return False
    cmd = ["uv", "run", str(script_path), str(WORKSPACE_PATH)]
    if extra_args:
        cmd.extend(extra_args)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            _log(f"{script_name} failed (exit {result.returncode}): {result.stderr[:200]}")
            return False
        return True
    except subprocess.TimeoutExpired:
        _log(f"{script_name} timed out (60s limit)")
        return False
    except Exception as exc:
        _log(f"{script_name} error: {exc}")
        return False


def main() -> int:
    try:
        if not SCRIPTS_DIR.exists():
            _log(f"temporal-self scripts not found: {SCRIPTS_DIR}")
            return 0

        transcripts_dir = _find_transcripts_dir()
        extra_ingest = []
        if transcripts_dir:
            extra_ingest = ["--transcripts", str(transcripts_dir)]

        _run_script("ingest.py", extra_ingest)
        _run_script("segment.py")
        _run_script("mine.py")

        return 0
    except Exception as exc:
        _log(f"unexpected error: {exc}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
