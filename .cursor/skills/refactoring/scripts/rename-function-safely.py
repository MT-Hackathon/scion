#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Preview or apply safe function renames using ripgrep discovery."""

from __future__ import annotations

import argparse
import difflib
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

RG_TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class FileChange:
    """Represents one file update for a symbol rename."""

    path: Path
    replacements: int
    before: str
    after: str


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Rename function symbol references with preview-by-default behavior."
    )
    parser.add_argument("old_name", help="Existing function name.")
    parser.add_argument("new_name", help="New function name.")
    parser.add_argument("source_file", help="File containing the function definition.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes to files. Default is preview-only.",
    )
    return parser.parse_args()


def run_rg_files(symbol_pattern: str) -> list[Path]:
    """Return files referencing the old function symbol."""
    cmd = ["rg", "--files-with-matches", symbol_pattern, "."]
    result = subprocess.run(
        cmd,
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        timeout=RG_TIMEOUT_SECONDS,
        check=False,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stderr.strip() or "ripgrep failed")
    return [Path(line.strip()) for line in result.stdout.splitlines() if line.strip()]


def build_change(path: Path, compiled_symbol: re.Pattern[str], new_name: str) -> FileChange | None:
    """Build file change for symbol rename if replacements are found."""
    before = path.read_text(encoding="utf-8")
    after, replacements = compiled_symbol.subn(new_name, before)
    if replacements == 0:
        return None
    return FileChange(path=path, replacements=replacements, before=before, after=after)


def print_change(change: FileChange) -> None:
    """Print file-level summary and unified diff."""
    print(f"FILE\t{change.path}\treplacements={change.replacements}")
    diff_lines = difflib.unified_diff(
        change.before.splitlines(),
        change.after.splitlines(),
        fromfile=str(change.path),
        tofile=str(change.path),
        lineterm="",
    )
    for line in diff_lines:
        print(line)


def main() -> int:
    """Execute rename preview or apply flow."""
    try:
        args = parse_args()
        source_file = Path(args.source_file).expanduser().resolve()
        if not source_file.exists() or not source_file.is_file():
            print(f"Error: source file not found: {source_file}", file=sys.stderr)
            return 2

        symbol_regex = rf"\b{re.escape(args.old_name)}\b"
        compiled_symbol = re.compile(symbol_regex)
        files = run_rg_files(symbol_regex)
        if not files:
            print("SUMMARY\tfiles=0\treplacements=0\tmode=preview")
            return 0

        changes: list[FileChange] = []
        for file_path in files:
            if not file_path.exists() or not file_path.is_file():
                continue
            change = build_change(file_path, compiled_symbol, args.new_name)
            if change:
                changes.append(change)

        mode = "apply" if args.apply else "preview"
        total_replacements = sum(change.replacements for change in changes)

        for change in changes:
            print_change(change)
            if args.apply:
                change.path.write_text(change.after, encoding="utf-8")

        print(
            f"SUMMARY\tfiles={len(changes)}\treplacements={total_replacements}\tmode={mode}"
        )
        return 0
    except subprocess.TimeoutExpired:
        print(
            f"Error: ripgrep timed out after {RG_TIMEOUT_SECONDS} seconds.",
            file=sys.stderr,
        )
        return 1
    except UnicodeDecodeError as exc:
        print(f"Error: failed to read file as UTF-8: {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # Defensive catch for script reliability.
        print(f"Error: unexpected failure: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
