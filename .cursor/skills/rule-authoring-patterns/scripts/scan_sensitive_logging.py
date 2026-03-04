#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Scan the codebase for suspicious logging patterns that may leak secrets.

Usage:
  python .cursor/scripts/code-quality/scan_sensitive_logging.py

This is intentionally heuristic: it flags likely-problematic logs for human review.
It does not attempt to prove the absence of leaks.
"""

from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = PROJECT_ROOT / "src" / "backend"

LOG_CALL_RE = re.compile(r"\blogger\.(debug|info|warning|error|exception)\(")
SUSPECT_RE = re.compile(
    r"(?i)\b(password|passwd|pwd|secret|token|api[_-]?key|authorization|bearer|cookie)\b"
)


def main() -> int:
    if not BACKEND_ROOT.exists():
        raise RuntimeError(f"Backend root not found: {BACKEND_ROOT}")

    hits = []
    for path in BACKEND_ROOT.rglob("*.py"):
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue

        if not LOG_CALL_RE.search(text):
            continue

        for idx, line in enumerate(text.splitlines(), start=1):
            if "logger." not in line:
                continue
            if not SUSPECT_RE.search(line):
                continue
            hits.append((path, idx, line.strip()))

    if not hits:
        print("OK: no suspicious secret-ish logger lines found.")
        return 0

    print("Suspicious logging lines (review for secret leakage):")
    for path, idx, line in hits:
        rel = path.relative_to(PROJECT_ROOT)
        print(f"- {rel}:{idx}: {line}")

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
