#!/usr/bin/env -S uv run --python 3.12
"""DEPRECATED: Use git-pipeline.py trace instead."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

print(
    "WARNING: fetch_job_trace.py is deprecated. Use: git-pipeline.py trace",
    file=sys.stderr,
)

script_dir = Path(__file__).resolve().parent
script_path = script_dir / "git-pipeline.py"
new_args = ["trace"] + sys.argv[1:]

sys.exit(subprocess.call(["uv", "run", str(script_path)] + new_args))
