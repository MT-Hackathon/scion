#!/usr/bin/env -S uv run --python 3.12
"""DEPRECATED: Use git-milestone.py instead."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

print(
    "WARNING: manage_milestones.py is deprecated. Use: git-milestone.py",
    file=sys.stderr,
)

script_dir = Path(__file__).resolve().parent
script_path = script_dir / "git-milestone.py"
new_args = sys.argv[1:]

sys.exit(subprocess.call(["uv", "run", str(script_path)] + new_args))
