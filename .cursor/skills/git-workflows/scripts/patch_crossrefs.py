#!/usr/bin/env -S uv run --python 3.12
"""DEPRECATED: Use git-sync.py crossrefs instead."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

print(
    "WARNING: patch_crossrefs.py is deprecated. Use: git-sync.py crossrefs",
    file=sys.stderr,
)

script_dir = Path(__file__).resolve().parent
script_path = script_dir / "git-sync.py"
new_args = ["crossrefs"] + sys.argv[1:]

sys.exit(subprocess.call(["uv", "run", str(script_path)] + new_args))
