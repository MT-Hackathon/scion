#!/usr/bin/env -S uv run --python 3.12
"""DEPRECATED: Use git-issue.py triage instead."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

print(
    "WARNING: bulk_triage_issues.py is deprecated. Use: git-issue.py triage",
    file=sys.stderr,
)

script_dir = Path(__file__).resolve().parent
script_path = script_dir / "git-issue.py"
new_args = ["triage"] + sys.argv[1:]

sys.exit(subprocess.call(["uv", "run", str(script_path)] + new_args))
