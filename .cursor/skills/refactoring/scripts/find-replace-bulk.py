#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Preview or apply bulk find/replace changes with ripgrep-based discovery."""

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
    """Represents a pending file update and its replacement count."""

    path: Path
    replacements: int
    before: str
    after: str


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Find/replace across files with preview-by-default behavior."
    )
    parser.add_argument("find_pattern", help="Regex pattern to find.")
    parser.add_argument("replace_text", help="Replacement text.")
    parser.add_argument("path", nargs="?", default=".", help="Path to scan (default: .).")
    parser.add_argument(
        "file_type",
        nargs="?",
        default=None,
        help="Optional ripgrep file type filter (for example: py, ts).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes to files. Default is preview-only.",
    )
    return parser.parse_args()


def run_rg_files(pattern: str, scan_path: Path, file_type: str | None) -> list[Path]:
    """Return files containing pattern using ripgrep."""
    cmd = ["rg", "--files-with-matches", pattern, str(scan_path)]
    if file_type:
        cmd.extend(["--type", file_type])

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

    files = [Path(line.strip()) for line in result.stdout.splitlines() if line.strip()]
    return files


def build_change(path: Path, pattern: re.Pattern[str], replace_text: str) -> FileChange | None:
    """Build a change object for one file when replacements are present."""
    before = path.read_text(encoding="utf-8")
    after, replacements = pattern.subn(replace_text, before)
    if replacements == 0:
        return None
    return FileChange(path=path, replacements=replacements, before=before, after=after)


def print_diff(change: FileChange) -> None:
    """Print unified diff for one file change."""
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


def apply_change(change: FileChange) -> None:
    """Write file updates to disk."""
    change.path.write_text(change.after, encoding="utf-8")


def main() -> int:
    """Execute bulk find/replace in preview or apply mode."""
    try:
        args = parse_args()
        scan_path = Path(args.path).expanduser().resolve()
        if not scan_path.exists():
            print(f"Error: path does not exist: {scan_path}", file=sys.stderr)
            return 2
        if not scan_path.is_dir():
            print(f"Error: path is not a directory: {scan_path}", file=sys.stderr)
            return 2

        compiled = re.compile(args.find_pattern)
        files = run_rg_files(args.find_pattern, scan_path, args.file_type)
        if not files:
            print("SUMMARY\tfiles=0\treplacements=0\tmode=preview")
            return 0

        changes: list[FileChange] = []
        for file_path in files:
            if not file_path.exists() or not file_path.is_file():
                continue
            change = build_change(file_path, compiled, args.replace_text)
            if change:
                changes.append(change)

        mode = "apply" if args.apply else "preview"
        total_replacements = sum(change.replacements for change in changes)
        for change in changes:
            print_diff(change)
            if args.apply:
                apply_change(change)

        print(
            f"SUMMARY\tfiles={len(changes)}\treplacements={total_replacements}\tmode={mode}"
        )
        return 0
    except re.error as exc:
        print(f"Error: invalid regex pattern: {exc}", file=sys.stderr)
        return 2
    except UnicodeDecodeError as exc:
        print(f"Error: failed to read file as UTF-8: {exc}", file=sys.stderr)
        return 1
    except subprocess.TimeoutExpired:
        print(
            f"Error: ripgrep timed out after {RG_TIMEOUT_SECONDS} seconds.",
            file=sys.stderr,
        )
        return 1
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # Defensive catch for script reliability.
        print(f"Error: unexpected failure: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
