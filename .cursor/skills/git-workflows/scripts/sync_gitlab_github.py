#!/usr/bin/env -S uv run --python 3.12
"""DEPRECATED: Use git-sync.py mirror instead."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

print(
    "WARNING: sync_gitlab_github.py is deprecated. Use: git-sync.py mirror",
    file=sys.stderr,
)

script_dir = Path(__file__).resolve().parent
script_path = script_dir / "git-sync.py"
new_args = ["mirror"] + sys.argv[1:]

sys.exit(subprocess.call(["uv", "run", str(script_path)] + new_args))
