#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Scan for common linter patterns using ripgrep."""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

RG_TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class PatternSpec:
    """Represents one scan category and its ripgrep pattern."""

    label: str
    regex: str
    file_type: str | None = None


def parse_args() -> argparse.Namespace:
    """Parse and validate command-line arguments."""
    parser = argparse.ArgumentParser(description="Find common linting issues quickly.")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--ts", action="store_true", help="Scan TypeScript only.")
    mode_group.add_argument("--py", action="store_true", help="Scan Python only.")
    mode_group.add_argument("--all", action="store_true", help="Scan all file types.")
    parser.add_argument(
        "--path",
        default=".",
        help="Directory path to scan (default: current directory).",
    )
    return parser.parse_args()


def resolve_mode(args: argparse.Namespace) -> str:
    """Resolve scan mode with --all as the default."""
    if args.ts:
        return "ts"
    if args.py:
        return "py"
    return "all"


def run_count(spec: PatternSpec, scan_path: Path, mode: str) -> tuple[int, int]:
    """Run ripgrep count query and return total matches and file count."""
    cmd = ["rg", "--count", "--no-heading", spec.regex, str(scan_path)]

    mode_type_map = {
        "ts": "ts",
        "py": "py",
        "all": None,
    }
    rg_type = mode_type_map.get(mode)
    effective_type = rg_type or spec.file_type
    if effective_type:
        cmd.extend(["--type", effective_type])

    result = subprocess.run(
        cmd,
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        timeout=RG_TIMEOUT_SECONDS,
        check=False,
    )

    if result.returncode not in (0, 1):
        stderr = result.stderr.strip()
        raise RuntimeError(f"ripgrep failed for '{spec.label}': {stderr}")

    total = 0
    files = 0
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.rsplit(":", 1)
        if len(parts) != 2:
            continue
        try:
            count = int(parts[1])
        except ValueError:
            continue
        files += 1
        total += count
    return total, files


def build_specs(mode: str) -> list[PatternSpec]:
    """Build applicable scan categories for the selected mode."""
    specs: list[PatternSpec] = [
        PatternSpec("trailing_whitespace", r" $"),
        PatternSpec("console_or_print", r"console\.(log|warn|error|debug)|^\s*print\("),
        PatternSpec("todo_comments", r"TODO|FIXME|HACK|XXX"),
    ]

    if mode in {"ts", "all"}:
        specs.append(PatternSpec("typescript_any_usage", r":\s*any\b|as\s+any\b", "ts"))
    if mode in {"py", "all"}:
        specs.append(PatternSpec("python_long_lines_over_100", r".{101,}", "py"))
        specs.append(PatternSpec("python_multi_imports", r"^\s*import\s+[^#\n]*,\s*", "py"))
    return specs


def main() -> int:
    """Execute scan and print category summary."""
    try:
        args = parse_args()
        mode = resolve_mode(args)
        scan_path = Path(args.path).expanduser().resolve()
        if not scan_path.exists():
            print(f"Error: path does not exist: {scan_path}", file=sys.stderr)
            return 2
        if not scan_path.is_dir():
            print(f"Error: path is not a directory: {scan_path}", file=sys.stderr)
            return 2

        specs = build_specs(mode)
        print(f"MODE\t{mode}")
        print(f"PATH\t{scan_path}")

        totals: dict[str, tuple[int, int]] = {}
        for spec in specs:
            totals[spec.label] = run_count(spec, scan_path, mode)
            count, files = totals[spec.label]
            print(f"CATEGORY\tname={spec.label}\tmatches={count}\tfiles={files}")

        total_matches = sum(item[0] for item in totals.values())
        print(f"SUMMARY\ttotal_categories={len(totals)}\ttotal_matches={total_matches}")
        return 0
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
