#!/usr/bin/env -S uv run --python 3.12
"""DEPRECATED: Use git-label.py instead."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

print(
    "WARNING: manage_labels.py is deprecated. Use: git-label.py",
    file=sys.stderr,
)

script_dir = Path(__file__).resolve().parent
script_path = script_dir / "git-label.py"
new_args = sys.argv[1:]

sys.exit(subprocess.call(["uv", "run", str(script_path)] + new_args))
