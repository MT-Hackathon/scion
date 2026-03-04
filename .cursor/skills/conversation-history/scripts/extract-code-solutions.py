#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Description: Extract reusable code blocks and solutions from past conversations
Usage: extract-code-solutions.py PROJECT_PATH [LANGUAGE] [MIN_LENGTH]
"""

import argparse
import json
import sys
from collections import defaultdict
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
DEFAULT_MIN_LENGTH = 20
DATA_DIR_NAME = "data"
MAX_SAMPLE_CODE_LINES = 10
MAX_CODE_PREVIEW_LENGTH = 500
MAX_SAMPLE_BLOCKS = 5


# Pattern category keywords
ERROR_HANDLING_TERMS = ['error', 'exception', 'try', 'except', 'catch', 'raise']
API_INTEGRATION_TERMS = ['api', 'request', 'response', 'http', 'fetch', 'axios']
DATA_TRANSFORMATION_TERMS = ['transform', 'map', 'filter', 'reduce', 'parse']
CONFIGURATION_TERMS = ['config', 'setting', 'env', 'yaml', 'json']
TESTING_TERMS = ['test', 'assert', 'mock', 'fixture']
PATTERN_CATEGORY_TERMS = {
    'error_handling': ERROR_HANDLING_TERMS,
    'api_integration': API_INTEGRATION_TERMS,
    'data_transformation': DATA_TRANSFORMATION_TERMS,
    'configuration': CONFIGURATION_TERMS,
    'testing': TESTING_TERMS,
}


def categorize_code_pattern(code: str, language: str) -> str:
    """Categorize code pattern based on content."""
    # Guard: Validate inputs
    if not code:
        return 'general'

    code_lower = code.lower()

    for category, terms in PATTERN_CATEGORY_TERMS.items():
        if any(term in code_lower for term in terms):
            return category

    return 'general'


def _print_database_error() -> None:
    """Print database error message and exit."""
    print("Error: Cursor database not found.")
    print("Set CURSOR_DB_PATH environment variable to your database location:")
    print("  Linux: ~/.config/Cursor/User/globalStorage/state.vscdb")
    print(r"  Windows: C:\Users\<USERNAME>\AppData\Roaming\Cursor\User\globalStorage\state.vscdb")
    print("  macOS: ~/Library/Application Support/Cursor/User/globalStorage/state.vscdb")
    sys.exit(2)


def _filter_project_conversations(
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


def _extract_all_code_blocks(
    project_conversations: dict[str, list[dict[str, Any]]],
    language: str | None,
    min_length: int
) -> list[dict[str, Any]]:
    """Extract all code blocks from project conversations."""
    # Guard: Validate input
    if not project_conversations:
        return []

    all_code_blocks: list[dict[str, Any]] = []

    for conv_id, messages in project_conversations.items():
        code_blocks = extract_code_blocks(messages, language, min_length)
        files = find_files_in_conversation(messages)
        conv_date = get_conversation_date(messages)

        for cb in code_blocks:
            cb['conversation_id'] = conv_id
            cb['files'] = list(files)
            cb['date'] = conv_date.isoformat() if conv_date else None
            cb['pattern_category'] = categorize_code_pattern(cb['code'], cb['language'])
            all_code_blocks.append(cb)

    return all_code_blocks


def _group_by_language(code_blocks: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group code blocks by language."""
    # Guard: Validate input
    if not code_blocks:
        return {}

    by_language: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for cb in code_blocks:
        lang = cb.get('language', 'unknown')
        by_language[lang].append(cb)

    return dict(by_language)


def _group_by_category(code_blocks: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group code blocks by pattern category."""
    # Guard: Validate input
    if not code_blocks:
        return {}

    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for cb in code_blocks:
        category = cb.get('pattern_category', 'general')
        by_category[category].append(cb)

    return dict(by_category)


def _display_results(
    by_language: dict[str, list[dict[str, Any]]],
    by_category: dict[str, list[dict[str, Any]]],
    all_code_blocks: list[dict[str, Any]]
) -> None:
    """Display extraction results."""
    print("=" * 60)
    print("CODE SOLUTION EXTRACTION RESULTS")
    print("=" * 60)
    print("")

    print("1. CODE BLOCKS BY LANGUAGE")
    for lang, blocks in sorted(by_language.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"   {lang}: {len(blocks)} blocks")
    print("")

    print("2. PATTERN CATEGORIZATION")
    for category, blocks in sorted(by_category.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"   {category}: {len(blocks)} blocks")
    print("")

    # Show sample code blocks
    print("3. SAMPLE CODE BLOCKS")
    print("")

    sorted_blocks = sorted(all_code_blocks, key=lambda x: x.get('line_count', 0), reverse=True)
    for shown, cb in enumerate(sorted_blocks):
        if shown >= MAX_SAMPLE_BLOCKS:
            break

        print(f"   [{cb['language']}] {cb['pattern_category']} ({cb['line_count']} lines)")
        print(f"   Conversation: {cb['conversation_id'][:8]}...")
        if cb.get('files'):
            print(f"   Files: {', '.join(cb['files'][:3])}")

        # Show first few lines of code
        code_lines = cb['code'].split('\n')[:MAX_SAMPLE_CODE_LINES]
        print("   Code preview:")
        for line in code_lines:
            print(f"     {line}")
        if cb['line_count'] > MAX_SAMPLE_CODE_LINES:
            print(f"     ... ({cb['line_count'] - MAX_SAMPLE_CODE_LINES} more lines)")
        print()


def _save_results(
    output_file: Path,
    project_path: str,
    language: str | None,
    min_length: int,
    all_code_blocks: list[dict[str, Any]],
    by_language: dict[str, list[dict[str, Any]]],
    by_category: dict[str, list[dict[str, Any]]]
) -> None:
    """Save extraction results to JSON file."""
    # Guard: Validate inputs
    if not output_file or not project_path:
        return

    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump({
                'project': project_path,
                'language_filter': language,
                'min_length': min_length,
                'total_blocks': len(all_code_blocks),
                'by_language': {lang: len(blocks) for lang, blocks in by_language.items()},
                'by_category': {cat: len(blocks) for cat, blocks in by_category.items()},
                'code_blocks': all_code_blocks
            }, f, indent=2)
        print(f"\nResults saved to: {output_file}")
    except OSError as e:
        print(f"\nWarning: Unable to save results: {e}", file=sys.stderr)


def extract_code_solutions(
    project_path: str,
    language: str | None = None,
    min_length: int = DEFAULT_MIN_LENGTH
) -> None:
    """Extract reusable code patterns from conversation history."""
    # Guard: Validate project_path
    if not project_path:
        print("Error: Project path is required", file=sys.stderr)
        sys.exit(2)

    # Guard: Validate min_length
    if min_length < 0:
        min_length = DEFAULT_MIN_LENGTH

    db_path = get_cursor_db_path()
    if not db_path:
        _print_database_error()

    print(f"Extracting code from project: {project_path}")
    if language:
        print(f"Language filter: {language}")
    print(f"Minimum code length: {min_length} lines")
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
    project_conversations = _filter_project_conversations(all_conversations, project_path)
    print(f"Found {len(project_conversations)} project conversations")
    print("")

    # Extract code blocks
    print("Extracting code blocks...")
    all_code_blocks = _extract_all_code_blocks(project_conversations, language, min_length)
    print(f"Found {len(all_code_blocks)} code blocks")
    print("")

    # Group by language and category
    by_language = _group_by_language(all_code_blocks)
    by_category = _group_by_category(all_code_blocks)

    # Display results
    _display_results(by_language, by_category, all_code_blocks)

    # Save to JSON
    output_file = Path(__file__).parent.parent.parent.parent / DATA_DIR_NAME / f"code-solutions-{project_path.lower()}.json"
    _save_results(
        output_file,
        project_path,
        language,
        min_length,
        all_code_blocks,
        by_language,
        by_category
    )


if __name__ == '__main__':
    # Guard: Validate arguments
    parser = argparse.ArgumentParser(
        description="Extract reusable code blocks from project conversation history."
    )
    parser.add_argument("project_path", help="Project path/name to filter conversations")
    parser.add_argument("language", nargs="?", default=None, help="Optional language filter")
    parser.add_argument(
        "min_length",
        nargs="?",
        default=None,
        help=f"Minimum code length to include (default: {DEFAULT_MIN_LENGTH})",
    )

    args = parser.parse_args()

    project = args.project_path
    # Guard: Validate project path
    if not project:
        print("Error: Project path cannot be empty", file=sys.stderr)
        sys.exit(2)

    lang = args.language

    # Guard: Parse and validate min_length
    min_len = DEFAULT_MIN_LENGTH
    if args.min_length is not None:
        try:
            min_len = int(args.min_length)
            if min_len < 0:
                min_len = DEFAULT_MIN_LENGTH
        except (TypeError, ValueError):
            print(f"Warning: Invalid min_length value, using default {DEFAULT_MIN_LENGTH}", file=sys.stderr)
            min_len = DEFAULT_MIN_LENGTH

    extract_code_solutions(project, lang, min_len)
