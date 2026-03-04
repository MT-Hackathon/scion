#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Graft CLI bootstrap — delegates to installed graft package."""
from __future__ import annotations
import sys

def main() -> int:
    try:
        from graft.cli import main as graft_main
        return graft_main()
    except ImportError:
        print(
            "Error: graft library not installed.\n"
            "Install it with: pip install -e path/to/rootstock/app/backend\n"
            "Or use the native Tauri desktop app, or the graft-cli Rust binary.",
            file=sys.stderr,
        )
        return 1

if __name__ == "__main__":
    sys.exit(main())