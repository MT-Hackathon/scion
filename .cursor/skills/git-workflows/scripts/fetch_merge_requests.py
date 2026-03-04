#!/usr/bin/env -S uv run --python 3.12
"""DEPRECATED: Use git-mr.py list instead."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

print(
    "WARNING: fetch_merge_requests.py is deprecated. Use: git-mr.py list",
    file=sys.stderr,
)

script_dir = Path(__file__).resolve().parent
script_path = script_dir / "git-mr.py"
new_args = ["list"] + sys.argv[1:]

sys.exit(subprocess.call(["uv", "run", str(script_path)] + new_args))
