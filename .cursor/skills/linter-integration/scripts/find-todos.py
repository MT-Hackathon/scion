#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Search files for TODO-style markers using ripgrep."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable

DEFAULT_PATTERNS = "TODO|FIXME|HACK|XXX"
RG_TIMEOUT_SECONDS = 30


def parse_args() -> argparse.Namespace:
    """Parse and validate command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Find TODO/FIXME/HACK/XXX markers with summary counts."
    )
    parser.add_argument(
        "--patterns",
        default=DEFAULT_PATTERNS,
        help='Regex alternation to search for (default: "TODO|FIXME|HACK|XXX").',
    )
    parser.add_argument(
        "--path",
        default=".",
        help="Directory path to scan (default: current directory).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with status 1 when no matches are found.",
    )
    return parser.parse_args()


def extract_pattern_keys(patterns: str) -> list[str]:
    """Extract pattern labels for summary reporting."""
    keys = [part.strip() for part in patterns.split("|") if part.strip()]
    return keys if keys else [patterns]


def run_rg(patterns: str, scan_path: Path) -> subprocess.CompletedProcess[str]:
    """Execute ripgrep and return the completed process."""
    cmd = [
        "rg",
        "--json",
        "--line-number",
        "--no-heading",
        patterns,
        str(scan_path),
    ]
    return subprocess.run(
        cmd,
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        timeout=RG_TIMEOUT_SECONDS,
        check=False,
    )


def collect_matches(
    output_lines: Iterable[str], pattern_keys: list[str]
) -> tuple[list[tuple[str, int, str]], Counter[str], set[str]]:
    """Collect match rows and counters from ripgrep JSON output."""
    key_counts: Counter[str] = Counter({key: 0 for key in pattern_keys})
    files: set[str] = set()
    rows: list[tuple[str, int, str]] = []

    for line in output_lines:
        if not line.strip():
            continue
        payload = json.loads(line)
        if payload.get("type") != "match":
            continue

        data = payload["data"]
        file_path = data["path"]["text"]
        line_number = int(data["line_number"])
        text = data["lines"]["text"].rstrip("\n")
        rows.append((file_path, line_number, text))
        files.add(file_path)

        for key in pattern_keys:
            key_counts[key] += len(re.findall(key, text))

    return rows, key_counts, files


def print_results(
    rows: list[tuple[str, int, str]], key_counts: Counter[str], files: set[str]
) -> None:
    """Print match rows and end summary."""
    for file_path, line_number, text in rows:
        print(f"MATCH\tfile={file_path}\tline={line_number}\ttext={text}")

    total_matches = sum(key_counts.values())
    summary_parts = [f"{key}={key_counts[key]}" for key in key_counts]
    summary = " ".join(summary_parts)
    print(
        f"SUMMARY\ttotal_matches={total_matches}\ttotal_files={len(files)}\t{summary}".rstrip()
    )


def main() -> int:
    """Run TODO pattern search and return process exit code."""
    try:
        args = parse_args()
        scan_path = Path(args.path).expanduser().resolve()

        if not scan_path.exists():
            print(f"Error: path does not exist: {scan_path}", file=sys.stderr)
            return 2
        if not scan_path.is_dir():
            print(f"Error: path is not a directory: {scan_path}", file=sys.stderr)
            return 2

        pattern_keys = extract_pattern_keys(args.patterns)
        rg_result = run_rg(args.patterns, scan_path)

        if rg_result.returncode not in (0, 1):
            print("Error: ripgrep failed.", file=sys.stderr)
            if rg_result.stderr:
                print(rg_result.stderr.strip(), file=sys.stderr)
            return 1

        rows, key_counts, files = collect_matches(
            rg_result.stdout.splitlines(), pattern_keys
        )
        print_results(rows, key_counts, files)

        if not rows and args.strict:
            return 1
        return 0
    except subprocess.TimeoutExpired:
        print(
            f"Error: ripgrep timed out after {RG_TIMEOUT_SECONDS} seconds.",
            file=sys.stderr,
        )
        return 1
    except json.JSONDecodeError as exc:
        print(f"Error: failed to parse ripgrep output: {exc}", file=sys.stderr)
        return 1
    except re.error as exc:
        print(f"Error: invalid regex pattern: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # Defensive catch for script reliability.
        print(f"Error: unexpected failure: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
