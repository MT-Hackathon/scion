#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Description: Analyze project-scoped development patterns and file change frequency
Usage: analyze-project-evolution.py PROJECT_PATH [--days DAYS_BACK]
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from db_utils import (
    extract_code_blocks,
    extract_conversations,
    find_files_in_conversation,
    get_conversation_date,
    get_cursor_db_path,
    is_project_conversation,
    load_database,
)

# Constants
DEFAULT_DAYS_BACK = 60
TOP_FILES_COUNT = 10
TOP_WEEKS_COUNT = 10
TOP_FILES_EXPORT = 20
DATA_DIR_NAME = "data"


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

    project_conversations: dict[str, list[dict[str, Any]]] = {}
    for conv_id, messages in all_conversations.items():
        if is_project_conversation(messages, project_path):
            project_conversations[conv_id] = messages

    return project_conversations


def _filter_by_date(
    conversations: dict[str, list[dict[str, Any]]],
    days_back: int
) -> dict[str, list[dict[str, Any]]]:
    """Filter conversations by date range."""
    # Guard: Validate inputs
    if not conversations or days_back <= 0:
        return {}

    cutoff_date = datetime.now() - timedelta(days=days_back)
    date_filtered: dict[str, list[dict[str, Any]]] = {}

    for conv_id, messages in conversations.items():
        conv_date = get_conversation_date(messages)
        if conv_date is None or conv_date >= cutoff_date:
            date_filtered[conv_id] = messages

    return date_filtered


def _analyze_file_activity(
    conversations: dict[str, list[dict[str, Any]]]
) -> tuple[Counter[str], dict[str, list[datetime]]]:
    """Analyze file activity from conversations."""
    # Guard: Validate input
    if not conversations:
        return Counter(), {}

    file_counts: Counter[str] = Counter()
    file_dates: dict[str, list[datetime]] = defaultdict(list)

    for _conv_id, messages in conversations.items():
        files = find_files_in_conversation(messages)
        conv_date = get_conversation_date(messages)

        for file_path in files:
            file_counts[file_path] += 1
            if conv_date:
                file_dates[file_path].append(conv_date)

    return file_counts, file_dates


def _analyze_languages(
    conversations: dict[str, list[dict[str, Any]]]
) -> Counter[str]:
    """Analyze language distribution from conversations."""
    # Guard: Validate input
    if not conversations:
        return Counter()

    language_counts: Counter[str] = Counter()

    for _conv_id, messages in conversations.items():
        code_blocks = extract_code_blocks(messages)
        for cb in code_blocks:
            lang = cb.get('language', 'unknown')
            language_counts[lang] += 1

    return language_counts


def _analyze_timeline(
    conversations: dict[str, list[dict[str, Any]]]
) -> dict[str, int]:
    """Analyze conversation timeline."""
    # Guard: Validate input
    if not conversations:
        return {}

    weekly_counts: dict[str, int] = defaultdict(int)

    for _conv_id, messages in conversations.items():
        conv_date = get_conversation_date(messages)
        if conv_date:
            week_key = conv_date.strftime('%Y-W%W')
            weekly_counts[week_key] += 1

    return dict(weekly_counts)


def _save_results(
    output_file: Path,
    project_path: str,
    days_back: int,
    conversations: dict[str, list[dict[str, Any]]],
    file_counts: Counter[str],
    language_counts: Counter[str],
    weekly_counts: dict[str, int]
) -> None:
    """Save analysis results to JSON file."""
    # Guard: Validate inputs
    if not output_file or not project_path:
        return

    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump({
                'project': project_path,
                'days_back': days_back,
                'total_conversations': len(conversations),
                'file_activity': dict(file_counts.most_common(TOP_FILES_EXPORT)),
                'language_distribution': dict(language_counts),
                'weekly_timeline': weekly_counts
            }, f, indent=2)
        print(f"Results saved to: {output_file}")
    except OSError as e:
        print(f"Warning: Unable to save results: {e}", file=sys.stderr)


def analyze_project_evolution(project_path: str, days_back: int = DEFAULT_DAYS_BACK) -> None:
    """Analyze project development patterns from conversation history."""
    # Guard: Validate project_path
    if not project_path:
        print("Error: Project path is required", file=sys.stderr)
        sys.exit(2)

    # Guard: Validate days_back
    if days_back <= 0:
        days_back = DEFAULT_DAYS_BACK

    db_path = get_cursor_db_path()
    if not db_path:
        _print_database_error()

    print(f"Analyzing project: {project_path}")
    print(f"Time range: Last {days_back} days")
    print(f"Database: {db_path}")
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

    # Filter by project
    print(f"Filtering for {project_path} project...")
    project_conversations = _filter_by_project(all_conversations, project_path)
    print(f"Found {len(project_conversations)} project conversations")

    # Filter by date
    conversations = _filter_by_date(project_conversations, days_back)
    print(f"Found {len(conversations)} conversations in date range")
    print("")

    # Analyze files
    file_counts, _file_dates = _analyze_file_activity(conversations)

    # Analyze languages
    language_counts = _analyze_languages(conversations)

    # Analyze timeline
    weekly_counts = _analyze_timeline(conversations)

    # Display results
    print("=" * 60)
    print("PROJECT EVOLUTION ANALYSIS")
    print("=" * 60)
    print("")

    print("1. FILE ACTIVITY")
    print(f"   Top {TOP_FILES_COUNT} most discussed files:")
    for file_path, count in file_counts.most_common(TOP_FILES_COUNT):
        print(f"     {count:3d}x  {file_path}")
    print("")

    print("2. LANGUAGE DISTRIBUTION")
    if language_counts:
        print("   Code blocks by language:")
        for lang, count in language_counts.most_common():
            print(f"     {lang}: {count} blocks")
    else:
        print("   No code blocks found")
    print("")

    print("3. DEVELOPMENT PATTERNS")
    print(f"   Total conversations: {len(conversations)}")
    print(f"   Total files discussed: {len(file_counts)}")
    print(f"   Total code blocks: {sum(language_counts.values())}")
    print("")

    print("4. EVOLUTION TIMELINE")
    print("   Conversations by week:")
    sorted_weeks = sorted(weekly_counts.keys())[-TOP_WEEKS_COUNT:]
    for week in sorted_weeks:
        print(f"     {week}: {weekly_counts[week]} conversations")
    print("")

    # Save results
    output_file = Path(__file__).parent.parent.parent.parent / DATA_DIR_NAME / f"project-evolution-{project_path.lower()}.json"
    _save_results(
        output_file,
        project_path,
        days_back,
        conversations,
        file_counts,
        language_counts,
        weekly_counts
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Analyze project-scoped development patterns and file change frequency',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s procurement-web
  %(prog)s procurement-web --days 90
  %(prog)s ./procurement-web -d 30
        """
    )

    parser.add_argument(
        'project_path',
        help='Project path to analyze (e.g., procurement-web, ./procurement-web, or path/to/project)'
    )
    parser.add_argument(
        '--days', '-d',
        type=int,
        default=DEFAULT_DAYS_BACK,
        dest='days_back',
        help=f'Number of days to analyze (default: {DEFAULT_DAYS_BACK})'
    )

    args = parser.parse_args()

    # Guard: Validate project path
    if not args.project_path or not args.project_path.strip():
        print("Error: Project path cannot be empty", file=sys.stderr)
        sys.exit(2)

    # Guard: Validate days_back
    days_back = args.days_back
    if days_back <= 0:
        print(f"Warning: Invalid days value ({days_back}), using default {DEFAULT_DAYS_BACK}", file=sys.stderr)
        days_back = DEFAULT_DAYS_BACK

    analyze_project_evolution(args.project_path, days_back)
