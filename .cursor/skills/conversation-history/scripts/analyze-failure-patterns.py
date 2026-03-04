#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Analyze chat history for failure patterns and identify gaps in rules system.
Extracts conversations, searches for failure indicators, and compares against existing rules.
"""

import json
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

# Add script directory to path for local imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from db_utils import ENV_DB_PATH_KEY, get_cursor_db_path, load_database  # noqa: E402

# Constants
DATA_DIR_NAME = "data"
PATTERNS_FILE_NAME = "failure-patterns-raw.json"
SAMPLE_TEXT_LIMIT = 500
MAX_SAMPLE_TEXTS = 3
MAX_MESSAGES_TO_CHECK = 10

DB_PATH = get_cursor_db_path()
PROJECT_NAME = "procurement-web"
PROJECT_PATH_PATTERNS = ["procurement-web", "procurement_web", "procurementweb"]

# Failure pattern search terms
MULTIPLE_ITERATIONS = [
    "fix again", "still broken", "doesn't work", "retry", "second attempt",
    "third time", "still not working", "again", "repeated", "multiple times",
    "tried again", "attempted again"
]

USER_CORRECTIONS = [
    "no that's wrong", "actually", "should be", "not what I wanted",
    "correction", "that's not right", "incorrect", "wrong approach",
    "that's not", "no,", "wait,", "actually,", "I meant"
]

INEFFICIENT_APPROACHES = [
    "inefficient", "slow", "better way", "optimize", "performance issue",
    "takes too long", "too slow", "performance", "faster", "optimization",
    "inefficient approach", "better approach"
]

REDUNDANT_WORK = [
    "already exists", "duplicate", "we already did", "redundant",
    "did this before", "already have", "already created", "already implemented"
]

CODE_BUGS = [
    "error", "bug", "broken", "fails", "failure", "exception", "traceback",
    "test failed", "doesn't work", "not working", "issue", "problem"
]

# Subagent orchestration patterns
SUBAGENT_MISSED = [
    "should have used", "should have delegated", "would be faster",
    "use subagent", "use Task", "dispatch to", "hand off",
    "too much context", "context bloat", "delegate this",
    "should delegate", "try using explore", "use explore"
]

SUBAGENT_REQUESTED = [
    "explore agent", "the-architect", "the-executor", "the-author",
    "the-qa-tester", "the-researcher", "the-visual-qa", "dispatch", "subagent",
    "Task tool", "generalPurpose", "parallel explore",
    # Legacy patterns for historical data
    "deep-code", "quick-code", "doc-writer", "reviewer agent", "test-validator"
]

PARALLELIZATION_MISSED = [
    "run in parallel", "simultaneously", "at the same time",
    "should be parallel", "one at a time", "sequential",
    "in parallel", "parallel dispatch", "concurrent"
]

PROMPT_QUALITY = [
    "didn't understand", "misunderstood", "wrong file",
    "different file", "not what I asked", "re-read the",
    "that's not the file", "read the wrong", "missing context"
]


# Note: load_database is imported from db_utils


def extract_conversations(conn: sqlite3.Connection) -> dict[str, list[dict[str, Any]]]:
    """Extract all conversations from database."""
    # Guard: Validate connection
    if not conn:
        raise ValueError("Database connection is required")

    cursor = conn.cursor()

    # Get all bubble entries
    cursor.execute("SELECT key, value FROM cursorDiskKV WHERE key LIKE 'bubbleId:%'")

    conversations: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for key, value in cursor.fetchall():
        # Guard: Validate key format
        if not key or not isinstance(key, str):
            continue

        # Parse key: bubbleId:{conversation_id}:{message_id}
        parts = key.split(':')
        if len(parts) >= 3:
            conv_id = parts[1]
            msg_id = parts[2] if len(parts) > 2 else None

            # Parse value
            try:
                if isinstance(value, bytes):
                    data = json.loads(value.decode('utf-8', errors='ignore'))
                else:
                    data = json.loads(value)

                conversations[conv_id].append({
                    'message_id': msg_id,
                    'data': data,
                    'key': key
                })
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                print(f"Warning: Error parsing bubble {key}: {e}", file=sys.stderr)
                continue
            except Exception as e:
                print(f"Warning: Unexpected error parsing bubble {key}: {e}", file=sys.stderr)
                continue

    return conversations


def is_universal_api_conversation(conv_messages: list[dict[str, Any]]) -> bool:
    """Check if conversation is related to procurement-web project."""
    # Guard: Validate input
    if not conv_messages:
        return False

    for msg in conv_messages:
        data = msg['data']

        # Check relevantFiles
        if data.get('relevantFiles'):
            for file_path in data['relevantFiles']:
                if any(pattern.lower() in str(file_path).lower() for pattern in PROJECT_PATH_PATTERNS):
                    return True

        # Check attachedFolders
        for folder_field in ['attachedFolders', 'attachedFoldersNew']:
            if data.get(folder_field):
                for folder in data[folder_field]:
                    if any(pattern.lower() in str(folder).lower() for pattern in PROJECT_PATH_PATTERNS):
                        return True

        # Check text content for project references
        if data.get('text'):
            text_lower = data['text'].lower()
            if any(pattern.lower() in text_lower for pattern in PROJECT_PATH_PATTERNS):
                return True

        # Check codebaseContextChunks
        if data.get('codebaseContextChunks'):
            for chunk in data['codebaseContextChunks']:
                chunk_str = json.dumps(chunk).lower()
                if any(pattern.lower() in chunk_str for pattern in PROJECT_PATH_PATTERNS):
                    return True

    return False


def search_text_for_patterns(text: str, patterns: list[str]) -> list[str]:
    """Search text for pattern matches (case-insensitive)."""
    # Guard: Validate inputs
    if not text or not patterns:
        return []

    text_lower = text.lower()
    matches: list[str] = []

    for pattern in patterns:
        # Guard: Validate pattern
        if pattern and pattern.lower() in text_lower:
            matches.append(pattern)

    return matches


def categorize_failure(conv_messages: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Categorize failure patterns in a conversation."""
    # Guard: Validate input
    if not conv_messages:
        return {
            'multiple_iterations': [],
            'user_corrections': [],
            'inefficient_approaches': [],
            'redundant_work': [],
            'code_bugs': [],
            'subagent_missed': [],
            'subagent_requested': [],
            'parallelization_missed': [],
            'prompt_quality': []
        }

    categories: dict[str, list[str]] = {
        'multiple_iterations': [],
        'user_corrections': [],
        'inefficient_approaches': [],
        'redundant_work': [],
        'code_bugs': [],
        'subagent_missed': [],
        'subagent_requested': [],
        'parallelization_missed': [],
        'prompt_quality': []
    }

    all_text: list[str] = []
    for msg in conv_messages:
        data = msg.get('data', {})

        # Collect all text content
        if data.get('text'):
            all_text.append(data['text'])
        if data.get('richText'):
            all_text.append(str(data['richText']))

    combined_text = ' '.join(all_text)

    # Search for patterns - general failure patterns
    categories['multiple_iterations'] = search_text_for_patterns(combined_text, MULTIPLE_ITERATIONS)
    categories['user_corrections'] = search_text_for_patterns(combined_text, USER_CORRECTIONS)
    categories['inefficient_approaches'] = search_text_for_patterns(combined_text, INEFFICIENT_APPROACHES)
    categories['redundant_work'] = search_text_for_patterns(combined_text, REDUNDANT_WORK)
    categories['code_bugs'] = search_text_for_patterns(combined_text, CODE_BUGS)

    # Search for patterns - subagent orchestration patterns
    categories['subagent_missed'] = search_text_for_patterns(combined_text, SUBAGENT_MISSED)
    categories['subagent_requested'] = search_text_for_patterns(combined_text, SUBAGENT_REQUESTED)
    categories['parallelization_missed'] = search_text_for_patterns(combined_text, PARALLELIZATION_MISSED)
    categories['prompt_quality'] = search_text_for_patterns(combined_text, PROMPT_QUALITY)

    return categories


def analyze_conversations() -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Main analysis function."""
    # Guard: Validate database path
    if not DB_PATH:
        print(f"Error: Cursor database not found. Set {ENV_DB_PATH_KEY} environment variable.", file=sys.stderr)
        sys.exit(2)

    print("=" * 80)
    print("FAILURE PATTERN ANALYSIS")
    print("=" * 80)
    print(f"\nDatabase: {DB_PATH}")
    print(f"Project: {PROJECT_NAME}")
    print(f"Started: {datetime.now().isoformat()}\n")

    # Load database
    print("Loading database...")
    try:
        conn = load_database()
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)
    except sqlite3.Error as e:
        print(f"Error: Failed to connect to database: {e}", file=sys.stderr)
        sys.exit(2)

    # Extract conversations
    print("Extracting conversations...")
    all_conversations = extract_conversations(conn)
    print(f"Found {len(all_conversations)} total conversations")

    # Filter for procurement-web
    print("\nFiltering for procurement-web project...")
    universal_api_convs: dict[str, list[dict[str, Any]]] = {}
    for conv_id, messages in all_conversations.items():
        if is_universal_api_conversation(messages):
            universal_api_convs[conv_id] = messages

    print(f"Found {len(universal_api_convs)} procurement-web conversations")

    # Analyze for failure patterns
    print("\nAnalyzing failure patterns...")
    failure_patterns: dict[str, dict[str, Any]] = {}

    for conv_id, messages in universal_api_convs.items():
        categories = categorize_failure(messages)

        # Only include if has any failure indicators
        if any(categories.values()):
            failure_patterns[conv_id] = {
                'messages': messages,
                'categories': categories,
                'message_count': len(messages)
            }

    print(f"Found {len(failure_patterns)} conversations with failure patterns")

    # Generate statistics
    stats = {
        'total_conversations': len(all_conversations),
        'universal_api_conversations': len(universal_api_convs),
        'failure_conversations': len(failure_patterns),
        'pattern_counts': defaultdict(int)
    }

    for _conv_id, data in failure_patterns.items():
        for category, matches in data['categories'].items():
            if matches:
                stats['pattern_counts'][category] += 1

    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)
    print(f"Total conversations: {stats['total_conversations']}")
    print(f"procurement-web conversations: {stats['universal_api_conversations']}")
    print(f"Conversations with failure patterns: {stats['failure_conversations']}")
    print("\nPattern counts:")
    for pattern, count in sorted(stats['pattern_counts'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {pattern}: {count}")

    conn.close()

    return failure_patterns, stats


if __name__ == "__main__":
    failure_patterns, stats = analyze_conversations()

    # Save results to JSON for further analysis
    output_file = Path(__file__).parent.parent.parent.parent / DATA_DIR_NAME / PATTERNS_FILE_NAME
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Prepare serializable data
    serializable_patterns: dict[str, dict[str, Any]] = {}
    for conv_id, data in failure_patterns.items():
        serializable_patterns[conv_id] = {
            'message_count': data['message_count'],
            'categories': dict(data['categories'].items()),
            'sample_texts': []
        }

        # Extract sample texts (first N messages with text)
        text_count = 0
        for msg in data['messages'][:MAX_MESSAGES_TO_CHECK]:
            msg_data = msg.get('data', {})
            if msg_data.get('text'):
                serializable_patterns[conv_id]['sample_texts'].append(
                    msg_data['text'][:SAMPLE_TEXT_LIMIT]
                )
                text_count += 1
                if text_count >= MAX_SAMPLE_TEXTS:
                    break

    try:
        with open(output_file, 'w') as f:
            json.dump({
                'stats': stats,
                'patterns': serializable_patterns
            }, f, indent=2)
        print(f"\nResults saved to: {output_file}")
    except OSError as e:
        print(f"Error: Failed to write output file: {e}", file=sys.stderr)
        sys.exit(1)
