#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Description: Print the most recent Cursor conversation for a project.
Usage: check-last-chat.py PROJECT_PATH [--limit N] [--message-limit M]
"""

from __future__ import annotations

import argparse
import sys
import textwrap
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).resolve().parent))

from db_utils import (  # type: ignore
    extract_conversations,
    find_files_in_conversation,
    get_conversation_date,
    get_cursor_db_path,
    is_project_conversation,
    load_database,
)

DEFAULT_LIMIT = 1
DEFAULT_MESSAGE_LIMIT = 40
TIMESTAMP_FIELDS = ["timestamp", "createdAt", "date", "time"]
TEXT_WRAP_WIDTH = 100


def _display_db_error() -> None:
    """Display help text when the Cursor DB cannot be located."""
    print("Error: Cursor database not found.")
    print("Set CURSOR_DB_PATH to your Cursor state.vscdb path.")
    print("  Linux: ~/.config/Cursor/User/globalStorage/state.vscdb")
    print(r"  Windows: C:\Users\<USER>\AppData\Roaming\Cursor\User\globalStorage\state.vscdb")
    print("  macOS: ~/Library/Application Support/Cursor/User/globalStorage/state.vscdb")


def _parse_message_timestamp(data: dict[str, Any]) -> datetime | None:
    """Parse any known timestamp field on a message."""
    for field in TIMESTAMP_FIELDS:
        if field not in data or data[field] in (None, ""):
            continue
        value = data[field]
        if isinstance(value, (int, float)):
            try:
                return datetime.fromtimestamp(value, tz=UTC).replace(tzinfo=None)
            except (OSError, OverflowError, ValueError):
                continue
        if isinstance(value, str):
            normalized = value.replace("Z", "+00:00")
            for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S"):
                try:
                    dt = datetime.strptime(normalized, fmt)
                    if dt.tzinfo:
                        dt = dt.astimezone(UTC).replace(tzinfo=None)
                    return dt
                except ValueError:
                    continue
    return None


def _conversation_timestamp(messages: Sequence[dict[str, Any]]) -> datetime | None:
    """Compute the latest timestamp contained in a conversation."""
    timestamps: list[datetime] = []
    for msg in messages:
        data = msg.get("data", {})
        ts = _parse_message_timestamp(data)
        if ts:
            timestamps.append(ts)
    if timestamps:
        return max(timestamps)
    return get_conversation_date(list(messages))  # type: ignore[arg-type]


def _extract_text(data: dict[str, Any]) -> str:
    """Extract human-readable text from a message."""
    if not data:
        return ""
    text = data.get("text")
    if isinstance(text, str) and text.strip():
        return text.strip()
    rich_text = data.get("richText")
    if isinstance(rich_text, str) and rich_text.strip():
        return rich_text.strip()
    codeblocks = data.get("codeblocks")
    if isinstance(codeblocks, list) and codeblocks:
        first = codeblocks[0]
        if isinstance(first, dict):
            code = first.get("code")
            if isinstance(code, str):
                return code.strip()
    return ""


def _message_role(data: dict[str, Any]) -> str:
    """Map Cursor message type values to readable roles."""
    message_type = data.get("type")
    if message_type == 1:
        return "user"
    if message_type == 2:
        return "assistant"
    return "system"


def _format_message(index: int, msg: dict[str, Any]) -> str:
    """Format a message for terminal output."""
    data = msg.get("data", {})
    role = _message_role(data)
    text = _extract_text(data)
    timestamp = _parse_message_timestamp(data)
    ts_label = timestamp.isoformat() if timestamp else "unknown-time"
    header = f"{index:02d}. [{role}] {ts_label}"
    if not text:
        return header
    wrapped = "\n".join(textwrap.wrap(text, width=TEXT_WRAP_WIDTH)) if text else ""
    if wrapped:
        return f"{header}\n    {wrapped.replace('\\n', '\\n    ')}"
    return header


def _sorted_messages(messages: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort messages by timestamp then fallback to original order."""
    annotated: list[tuple[int, datetime, dict[str, Any]]] = []
    for idx, msg in enumerate(messages):
        data = msg.get("data", {})
        ts = _parse_message_timestamp(data)
        if ts is None:
            ts = datetime.min
        annotated.append((idx, ts, msg))
    annotated.sort(key=lambda item: (item[1], item[0]))
    return [item[2] for item in annotated]


def _print_conversation(conv_id: str, messages: Sequence[dict[str, Any]], message_limit: int) -> None:
    """Print the requested slice of a conversation."""
    latest_ts = _conversation_timestamp(messages)
    files = sorted(find_files_in_conversation(list(messages)))
    print("=" * 80)
    print(f"Conversation: {conv_id}")
    print(f"Last updated: {latest_ts.isoformat() if latest_ts else 'unknown'}")
    print(f"Messages: {len(messages)}  Files referenced: {len(files)}")
    if files:
        print("Files:")
        for file_path in files[:20]:
            print(f"  - {file_path}")
        if len(files) > 20:
            print(f"  ... {len(files) - 20} more")
    print("-" * 80)
    ordered = _sorted_messages(messages)
    subset = ordered[-message_limit:] if message_limit < len(ordered) else ordered
    for idx, msg in enumerate(subset, 1):
        print(_format_message(idx, msg))
        print("")


def _load_project_conversations(project_path: str) -> dict[str, list[dict[str, Any]]]:
    """Load all project conversations from the Cursor DB."""
    db_path = get_cursor_db_path()
    if not db_path:
        _display_db_error()
        sys.exit(2)
    conn = load_database(db_path)
    try:
        all_conversations = extract_conversations(conn)
    finally:
        conn.close()
    project_convs: dict[str, list[dict[str, Any]]] = {}
    for conv_id, messages in all_conversations.items():
        if is_project_conversation(messages, project_path):
            project_convs[conv_id] = messages
    if not project_convs:
        print(f"No conversations found for project '{project_path}'.")
        sys.exit(0)
    return project_convs


def _select_latest_conversations(
    conversations: dict[str, list[dict[str, Any]]],
    limit: int,
) -> list[tuple[str, list[dict[str, Any]]]]:
    """Return the most recent conversations sorted by activity."""
    sortable: list[tuple[str, datetime | None, list[dict[str, Any]]]] = []
    for conv_id, messages in conversations.items():
        sortable.append((conv_id, _conversation_timestamp(messages), messages))
    sortable.sort(key=lambda item: item[1] or datetime.min, reverse=True)
    return [(conv_id, messages) for conv_id, _, messages in sortable[:limit]]


def main() -> None:
    # Reconfigure stdout to handle Unicode on Windows (cp1252 default can't handle → etc.)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # type: ignore[attr-defined]

    parser = argparse.ArgumentParser(
        description="Print the most recent Cursor conversation for a project.",
    )
    parser.add_argument("project_path", help="Project path or name (e.g., procurement-web)")
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"Number of conversations to print (default {DEFAULT_LIMIT})",
    )
    parser.add_argument(
        "--message-limit",
        type=int,
        default=DEFAULT_MESSAGE_LIMIT,
        help=f"Number of trailing messages to show per conversation (default {DEFAULT_MESSAGE_LIMIT})",
    )
    args = parser.parse_args()

    if args.limit <= 0:
        parser.error("--limit must be positive")
    if args.message_limit <= 0:
        parser.error("--message-limit must be positive")

    conversations = _load_project_conversations(args.project_path)
    latest = _select_latest_conversations(conversations, args.limit)
    for conv_id, messages in latest:
        _print_conversation(conv_id, messages, args.message_limit)


if __name__ == "__main__":
    main()
