#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Description: Find all conversations mentioning specific files
Usage: trace-file-discussions.py FILE_PATTERN [--project PROJECT_PATH]
"""

import argparse
import sys
from datetime import datetime
from typing import Any

from db_utils import (
    extract_conversations,
    file_matches_pattern,
    find_files_in_conversation,
    get_conversation_date,
    get_cursor_db_path,
    is_project_conversation,
    load_database,
)

# Constants
MAX_RESULTS = 20
MAX_FILES_DISPLAY = 5


def _print_database_error() -> None:
    """Print database error message and exit."""
    print("Error: Cursor database not found.")
    print("Set CURSOR_DB_PATH environment variable to your database location:")
    print("  Linux: ~/.config/Cursor/User/globalStorage/state.vscdb")
    print(r"  Windows: C:\Users\<USERNAME>\AppData\Roaming\Cursor\User\globalStorage\state.vscdb")
    print("  macOS: ~/Library/Application Support/Cursor/User/globalStorage/state.vscdb")
    sys.exit(2)


def _filter_by_project(
    all_conversations: dict[str, list[dict[str, Any]]],
    project_path: str
) -> dict[str, list[dict[str, Any]]]:
    """Filter conversations by project."""
    # Guard: Validate inputs
    if not all_conversations or not project_path:
        return {}

    filtered_conversations: dict[str, list[dict[str, Any]]] = {}
    for conv_id, messages in all_conversations.items():
        if is_project_conversation(messages, project_path):
            filtered_conversations[conv_id] = messages

    return filtered_conversations


def _find_file_matches(
    conversations: dict[str, list[dict[str, Any]]],
    file_pattern: str
) -> list[dict[str, Any]]:
    """Find conversations mentioning files matching pattern."""
    # Guard: Validate inputs
    if not conversations or not file_pattern:
        return []

    matches: list[dict[str, Any]] = []

    for conv_id, messages in conversations.items():
        files = find_files_in_conversation(messages)
        matching_files = [f for f in files if file_matches_pattern(f, file_pattern)]

        if matching_files:
            conv_date = get_conversation_date(messages)
            matches.append({
                'conversation_id': conv_id,
                'messages': messages,
                'date': conv_date,
                'message_count': len(messages),
                'matching_files': matching_files,
                'all_files': list(files)
            })

    # Sort by date (most recent first)
    matches.sort(key=lambda x: x['date'] if x['date'] else datetime.min, reverse=True)

    # Limit results
    return matches[:MAX_RESULTS]


def _display_results(matches: list[dict[str, Any]]) -> None:
    """Display file discussion results."""
    print(f"\nFound {len(matches)} conversations mentioning matching files:\n")

    for i, match in enumerate(matches, 1):
        print(f"{i}. Conversation {match['conversation_id'][:8]}...")
        if match['date']:
            print(f"   Date: {match['date'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Messages: {match['message_count']}")
        print(f"   Matching files: {', '.join(match['matching_files'][:MAX_FILES_DISPLAY])}")
        if len(match['matching_files']) > MAX_FILES_DISPLAY:
            print(f"   ... and {len(match['matching_files']) - MAX_FILES_DISPLAY} more")

        # Show related files
        related_files = [f for f in match['all_files'] if f not in match['matching_files']]
        if related_files:
            print(f"   Related files: {', '.join(related_files[:MAX_FILES_DISPLAY])}")

        print()


def trace_file_discussions(
    file_pattern: str,
    project_path: str | None = None
) -> list[dict[str, Any]]:
    """Find conversations mentioning files matching pattern."""
    # Guard: Validate file_pattern
    if not file_pattern:
        print("Error: File pattern is required", file=sys.stderr)
        sys.exit(2)

    db_path = get_cursor_db_path()
    if not db_path:
        _print_database_error()

    print(f"Tracing discussions for: {file_pattern}")
    if project_path:
        print(f"Project: {project_path}")
    print("")

    # Load database and extract conversations
    try:
        conn = load_database(db_path)
        all_conversations = extract_conversations(conn)
        conn.close()
    except Exception as e:
        print(f"Error: Failed to load database: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(all_conversations)} total conversations")

    # Filter by project if specified
    if project_path:
        print(f"Filtering for {project_path} project...")
        conversations = _filter_by_project(all_conversations, project_path)
        print(f"Found {len(conversations)} project conversations")
    else:
        conversations = all_conversations

    # Find conversations mentioning files matching pattern
    print(f"\nSearching for files matching '{file_pattern}'...")
    matches = _find_file_matches(conversations, file_pattern)

    # Display results
    _display_results(matches)

    return matches


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Find all conversations mentioning specific files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "config.py"
  %(prog)s "*.yaml" --project procurement-web
  %(prog)s "error_handling.py" -p ./procurement-web
        """
    )

    parser.add_argument(
        'file_pattern',
        help='File pattern to search for (e.g., config.py, *.yaml, error_handling.py)'
    )
    parser.add_argument(
        '--project', '-p',
        dest='project_path',
        help='Filter by project path (e.g., procurement-web, ./procurement-web, or path/to/project)'
    )

    args = parser.parse_args()

    # Guard: Validate file_pattern
    if not args.file_pattern or not args.file_pattern.strip():
        print("Error: File pattern cannot be empty", file=sys.stderr)
        sys.exit(2)

    trace_file_discussions(args.file_pattern, args.project_path)
