#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Description: Search conversations for technical patterns (errors, APIs, solutions)
Usage: find-solution-patterns.py SEARCH_TERM [--project PROJECT_PATH] [--days DAYS_BACK]
"""

import argparse
import sys
from datetime import datetime, timedelta
from typing import Any

from db_utils import (
    extract_conversations,
    find_files_in_conversation,
    get_conversation_date,
    get_cursor_db_path,
    is_project_conversation,
    load_database,
    search_text_in_conversation,
)

# Constants
DEFAULT_DAYS_BACK = 90
MAX_DAYS_BACK_THRESHOLD = 3650
MAX_RESULTS = 10
SAMPLE_TEXT_LENGTH = 200
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


def _filter_by_date(
    conversations: dict[str, list[dict[str, Any]]],
    days_back: int
) -> dict[str, list[dict[str, Any]]]:
    """Filter conversations by date range."""
    # Guard: Validate inputs
    if not conversations or days_back <= 0:
        return conversations

    # Guard: Only filter if reasonable range
    if days_back >= MAX_DAYS_BACK_THRESHOLD:
        return conversations

    cutoff_date = datetime.now() - timedelta(days=days_back)
    date_filtered: dict[str, list[dict[str, Any]]] = {}

    for conv_id, messages in conversations.items():
        conv_date = get_conversation_date(messages)
        if conv_date is None or conv_date >= cutoff_date:
            date_filtered[conv_id] = messages

    return date_filtered


def _find_matching_conversations(
    conversations: dict[str, list[dict[str, Any]]],
    search_term: str
) -> list[dict[str, Any]]:
    """Find conversations matching search term."""
    # Guard: Validate inputs
    if not conversations or not search_term:
        return []

    matches: list[dict[str, Any]] = []

    for conv_id, messages in conversations.items():
        if search_text_in_conversation(messages, search_term):
            conv_date = get_conversation_date(messages)
            matches.append({
                'conversation_id': conv_id,
                'messages': messages,
                'date': conv_date,
                'message_count': len(messages)
            })

    # Sort by date (most recent first)
    matches.sort(key=lambda x: x['date'] if x['date'] else datetime.min, reverse=True)

    # Limit results
    return matches[:MAX_RESULTS]


def _display_results(matches: list[dict[str, Any]]) -> None:
    """Display search results."""
    print(f"\nFound {len(matches)} matching conversations:\n")

    for i, match in enumerate(matches, 1):
        print(f"{i}. Conversation {match['conversation_id'][:8]}...")
        if match['date']:
            print(f"   Date: {match['date'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Messages: {match['message_count']}")

        # Extract sample text
        sample_texts: list[str] = []
        for msg in match['messages'][:3]:
            data = msg.get('data', {})
            if isinstance(data, dict) and 'text' in data and data['text']:
                text = str(data['text'])[:SAMPLE_TEXT_LENGTH].replace('\n', ' ')
                sample_texts.append(text)

        if sample_texts:
            print(f"   Sample: {sample_texts[0]}")

        # Extract file references
        files = find_files_in_conversation(match['messages'])
        if files:
            file_list = list(files)[:MAX_FILES_DISPLAY]
            print(f"   Files: {', '.join(file_list)}")

        print()


def find_solution_patterns(
    search_term: str,
    project_path: str | None = None,
    days_back: int = DEFAULT_DAYS_BACK
) -> list[dict[str, Any]]:
    """Search conversations for patterns matching search term."""
    # Guard: Validate search_term
    if not search_term:
        print("Error: Search term is required", file=sys.stderr)
        sys.exit(2)

    # Guard: Validate days_back
    if days_back <= 0:
        days_back = DEFAULT_DAYS_BACK

    db_path = get_cursor_db_path()
    if not db_path:
        _print_database_error()

    print(f"Searching for: {search_term}")
    if project_path:
        print(f"Project: {project_path}")
    print(f"Time range: Last {days_back} days")
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

    # Filter by date if specified
    conversations = _filter_by_date(conversations, days_back)
    if days_back < MAX_DAYS_BACK_THRESHOLD:
        print(f"Found {len(conversations)} conversations in date range")

    # Search for term
    print(f"\nSearching for '{search_term}'...")
    matches = _find_matching_conversations(conversations, search_term)

    # Display results
    _display_results(matches)

    return matches


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Search conversations for technical patterns (errors, APIs, solutions)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "rate limit error"
  %(prog)s "authentication" --project procurement-web
  %(prog)s "TypeError" --project procurement-web --days 30
  %(prog)s "UI" -p ./procurement-web -d 1
        """
    )

    parser.add_argument(
        'search_term',
        help='Text pattern to search for in conversations'
    )
    parser.add_argument(
        '--project', '-p',
        dest='project_path',
        help='Filter by project path (e.g., procurement-web, ./procurement-web, or path/to/project)'
    )
    parser.add_argument(
        '--days', '-d',
        type=int,
        default=DEFAULT_DAYS_BACK,
        dest='days_back',
        help=f'Number of days to search back (default: {DEFAULT_DAYS_BACK})'
    )

    args = parser.parse_args()

    # Guard: Validate search_term
    if not args.search_term or not args.search_term.strip():
        print("Error: Search term cannot be empty", file=sys.stderr)
        sys.exit(2)

    # Guard: Validate days_back
    days_back = args.days_back
    if days_back <= 0:
        print(f"Warning: Invalid days value ({days_back}), using default {DEFAULT_DAYS_BACK}", file=sys.stderr)
        days_back = DEFAULT_DAYS_BACK

    find_solution_patterns(args.search_term, args.project_path, days_back)
