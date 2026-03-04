#!/usr/bin/env -S uv run --python 3.12
"""DEPRECATED: Use git-epic.py instead."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

print(
    "WARNING: manage_epic.py is deprecated. Use: git-epic.py",
    file=sys.stderr,
)

script_dir = Path(__file__).resolve().parent
script_path = script_dir / "git-epic.py"
new_args = sys.argv[1:]

sys.exit(subprocess.call(["uv", "run", str(script_path)] + new_args))
