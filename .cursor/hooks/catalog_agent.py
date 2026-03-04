#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CATALOG_FILE = Path(__file__).resolve().parent.parent / "handoffs" / "agent-catalog.md"
SUMMARY_LENGTH = 150


def _clean_result(result: str | None) -> str:
    """Normalize result text and truncate it for cataloging."""
    if not result:
        return "no result text"

    normalized = " ".join(result.split())
    if len(normalized) <= SUMMARY_LENGTH:
        return normalized

    truncated = normalized[:SUMMARY_LENGTH].rstrip()
    return f"{truncated}..."


def _catalog_entry(event: dict[str, Any]) -> str:
    """Build the catalog entry line from the hook payload."""
    timestamp = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    subagent_type = event.get("subagent_type") or "unknown"
    conversation_id = event.get("conversation_id") or event.get("conversationId") or "unknown"
    result_summary = _clean_result(event.get("result"))
    status = event.get("status", "unknown")
    return f"- {timestamp} | {subagent_type} | {status} | {result_summary} | conversation_id={conversation_id}\n"


def _append_to_catalog(entry: str) -> None:
    """Ensure catalog directory exists and append the new entry."""
    catalog_dir = CATALOG_FILE.parent
    catalog_dir.mkdir(parents=True, exist_ok=True)
    with CATALOG_FILE.open("a", encoding="utf-8") as catalog:
        catalog.write(entry)


def main() -> int:
    """Parse stdin and add a catalog entry."""
    try:
        raw_input = sys.stdin.read()
        brace = raw_input.find("{")
        if brace > 0:
            raw_input = raw_input[brace:]
        if not raw_input.strip():
            return 0

        event = json.loads(raw_input)
        entry = _catalog_entry(event)
        _append_to_catalog(entry)
        return 0
    except Exception:  # pragma: no cover - best-effort hook should never fail
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
