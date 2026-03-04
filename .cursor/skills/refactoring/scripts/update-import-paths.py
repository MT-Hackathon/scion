#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Preview or apply import-path updates using ripgrep discovery."""

from __future__ import annotations

import argparse
import difflib
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

RG_TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class FileChange:
    """Represents one file change for import path updates."""

    path: Path
    replacements: int
    before: str
    after: str


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Update import path strings with preview-by-default behavior."
    )
    parser.add_argument("old_import", help="Old import text to replace.")
    parser.add_argument("new_import", help="New import text.")
    parser.add_argument("path", nargs="?", default=".", help="Path to scan (default: .).")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes to files. Default is preview-only.",
    )
    return parser.parse_args()


def run_rg_files(old_import: str, scan_path: Path) -> list[Path]:
    """Use ripgrep to find files containing target import text."""
    cmd = [
        "rg",
        "--files-with-matches",
        r"^\s*(from|import)\s+",
        str(scan_path),
    ]
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

    files: list[Path] = []
    for line in result.stdout.splitlines():
        file_path = Path(line.strip())
        if not file_path.exists() or not file_path.is_file():
            continue
        text = file_path.read_text(encoding="utf-8")
        if old_import in text:
            files.append(file_path)
    return files


def replace_imports(text: str, old_import: str, new_import: str) -> tuple[str, int]:
    """Replace old import text only on import-related lines."""
    lines = text.splitlines(keepends=True)
    updated: list[str] = []
    replacements = 0
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("import ") or stripped.startswith("from "):
            count = line.count(old_import)
            if count:
                line = line.replace(old_import, new_import)
                replacements += count
        updated.append(line)
    return "".join(updated), replacements


def print_change(change: FileChange) -> None:
    """Print file summary and unified diff."""
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
    """Execute preview/apply import path updates."""
    try:
        args = parse_args()
        scan_path = Path(args.path).expanduser().resolve()
        if not scan_path.exists():
            print(f"Error: path does not exist: {scan_path}", file=sys.stderr)
            return 2
        if not scan_path.is_dir():
            print(f"Error: path is not a directory: {scan_path}", file=sys.stderr)
            return 2

        candidate_files = run_rg_files(args.old_import, scan_path)
        if not candidate_files:
            print("SUMMARY\tfiles=0\treplacements=0\tmode=preview")
            return 0

        changes: list[FileChange] = []
        for file_path in candidate_files:
            before = file_path.read_text(encoding="utf-8")
            after, replacements = replace_imports(before, args.old_import, args.new_import)
            if replacements:
                changes.append(
                    FileChange(
                        path=file_path,
                        replacements=replacements,
                        before=before,
                        after=after,
                    )
                )

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
