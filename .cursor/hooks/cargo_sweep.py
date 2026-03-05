#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Stop hook: prune Rust build artifacts older than 2 days via cargo-sweep.

Runs after every Cursor session as a disk-space backstop. With consistent
session cadence, this keeps target/ bounded to roughly 2 sessions of artifacts.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


RETENTION_DAYS = 2


def _log(message: str) -> None:
    print(f"[cargo_sweep] {message}", file=sys.stderr, flush=True)


def _resolve_workspace() -> Path:
    file_path = globals().get("__file__")
    if file_path:
        return Path(file_path).resolve().parents[2]
    return Path.cwd()


def main() -> int:
    workspace = _resolve_workspace()
    target_dir = workspace / "target"

    if not target_dir.exists():
        _log("target/ not found — nothing to sweep")
        return 0

    cargo_sweep = shutil.which("cargo-sweep")
    if cargo_sweep is None:
        # Try the standard cargo bin location on Windows
        fallback = Path.home() / ".cargo" / "bin" / "cargo-sweep.exe"
        if fallback.exists():
            cargo_sweep = str(fallback)
        else:
            _log("cargo-sweep not found — skipping (install with: cargo install cargo-sweep)")
            return 0

    try:
        result = subprocess.run(
            [cargo_sweep, "sweep", "--time", str(RETENTION_DAYS)],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            _log(f"cargo-sweep failed (exit {result.returncode}): {result.stderr[:300]}")
            return 0

        output = result.stdout.strip()
        if output:
            _log(output)
        else:
            _log(f"sweep complete (>{RETENTION_DAYS}d artifacts pruned)")

        return 0
    except subprocess.TimeoutExpired:
        _log("cargo-sweep timed out (120s limit) — skipping")
        return 0
    except Exception as exc:
        _log(f"unexpected error: {exc}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
