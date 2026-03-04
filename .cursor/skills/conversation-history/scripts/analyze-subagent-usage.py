#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Analyze chat history for subagent usage patterns.
Tracks Task tool invocations, agent type distribution, and correlates with failure patterns.
"""

import json
import re
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
OUTPUT_FILE_NAME = "subagent-usage.json"
SAMPLE_TEXT_LIMIT = 500
MAX_MESSAGES_TO_CHECK = 50

DB_PATH = get_cursor_db_path()
PROJECT_NAME = "procurement-web"
PROJECT_PATH_PATTERNS = ["procurement-web", "procurement_web", "procurementweb"]

# Agent type patterns to search for
AGENT_TYPES = {
    'explore': [r'\bexplore\b', r'explore agent', r'thoroughness'],
    'the-architect': [r'the-architect', r'the_architect', r'architect agent', r'deep-code'],
    'the-executor': [r'the-executor', r'the_executor', r'executor agent', r'quick-code'],
    'the-author': [r'the-author', r'the_author', r'author agent', r'doc-writer'],
    'the-qa-tester': [r'the-qa-tester', r'the_qa_tester', r'qa agent', r'reviewer', r'test-validator'],
    'the-researcher': [r'the-researcher', r'the_researcher', r'researcher agent'],
    'the-visual-qa': [r'the-visual-qa', r'the_visual_qa', r'visual-qa', r'visual qa'],
    'generalPurpose': [r'generalPurpose', r'general-purpose', r'general purpose'],
    'shell': [r'\bshell\b', r'shell agent'],
}

# Subagent dispatch indicators
DISPATCH_PATTERNS = [
    r'dispatch', r'Task tool', r'subagent', r'parallel.*agent',
    r'launching.*agent', r'dispatching', r'hand.*off'
]


def extract_conversations(conn: sqlite3.Connection) -> dict[str, list[dict[str, Any]]]:
    """Extract all conversations from database."""
    if not conn:
        raise ValueError("Database connection is required")

    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM cursorDiskKV WHERE key LIKE 'bubbleId:%'")

    conversations: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for key, value in cursor.fetchall():
        if not key or not isinstance(key, str):
            continue

        parts = key.split(':')
        if len(parts) >= 3:
            conv_id = parts[1]
            msg_id = parts[2] if len(parts) > 2 else None

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
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            except Exception:
                continue

    return conversations


def is_project_conversation(conv_messages: list[dict[str, Any]]) -> bool:
    """Check if conversation is related to project."""
    if not conv_messages:
        return False

    for msg in conv_messages:
        data = msg.get('data', {})

        # Check relevantFiles
        if data.get('relevantFiles'):
            for file_path in data['relevantFiles']:
                if any(p.lower() in str(file_path).lower() for p in PROJECT_PATH_PATTERNS):
                    return True

        # Check attachedFolders
        for folder_field in ['attachedFolders', 'attachedFoldersNew']:
            if data.get(folder_field):
                for folder in data[folder_field]:
                    if any(p.lower() in str(folder).lower() for p in PROJECT_PATH_PATTERNS):
                        return True

        # Check text content
        if data.get('text'):
            text_lower = data['text'].lower()
            if any(p.lower() in text_lower for p in PROJECT_PATH_PATTERNS):
                return True

    return False


def analyze_subagent_usage(conv_messages: list[dict[str, Any]]) -> dict[str, Any]:
    """Analyze subagent usage in a conversation."""
    if not conv_messages:
        return {
            'agent_mentions': {},
            'dispatch_count': 0,
            'has_parallel_dispatch': False,
            'dispatch_patterns_found': []
        }

    # Collect all text
    all_text: list[str] = []
    for msg in conv_messages:
        data = msg.get('data', {})
        if data.get('text'):
            all_text.append(data['text'])
        if data.get('richText'):
            all_text.append(str(data['richText']))

    combined_text = ' '.join(all_text)
    combined_lower = combined_text.lower()

    # Count agent type mentions
    agent_mentions: dict[str, int] = {}
    for agent_type, patterns in AGENT_TYPES.items():
        count = 0
        for pattern in patterns:
            matches = re.findall(pattern, combined_lower, re.IGNORECASE)
            count += len(matches)
        if count > 0:
            agent_mentions[agent_type] = count

    # Count dispatch patterns
    dispatch_count = 0
    dispatch_patterns_found: list[str] = []
    for pattern in DISPATCH_PATTERNS:
        matches = re.findall(pattern, combined_lower, re.IGNORECASE)
        if matches:
            dispatch_count += len(matches)
            dispatch_patterns_found.append(pattern)

    # Check for parallel dispatch indicators
    parallel_patterns = [r'parallel', r'simultaneously', r'concurrent', r'at the same time']
    has_parallel = any(re.search(p, combined_lower) for p in parallel_patterns)

    return {
        'agent_mentions': agent_mentions,
        'dispatch_count': dispatch_count,
        'has_parallel_dispatch': has_parallel,
        'dispatch_patterns_found': list(set(dispatch_patterns_found))
    }


def calculate_usage_score(usage: dict[str, Any]) -> int:
    """Calculate a subagent usage score (0-100)."""
    score = 0

    # Points for agent mentions (max 40)
    total_mentions = sum(usage['agent_mentions'].values())
    score += min(40, total_mentions * 5)

    # Points for dispatch count (max 30)
    score += min(30, usage['dispatch_count'] * 10)

    # Points for parallel dispatch (20)
    if usage['has_parallel_dispatch']:
        score += 20

    # Points for using multiple agent types (10)
    if len(usage['agent_mentions']) >= 2:
        score += 10

    return min(100, score)


def analyze_all_conversations() -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Main analysis function."""
    if not DB_PATH:
        print(f"Error: Cursor database not found. Set {ENV_DB_PATH_KEY}.", file=sys.stderr)
        sys.exit(2)

    print("=" * 80)
    print("SUBAGENT USAGE ANALYSIS")
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

    # Filter for project
    print(f"\nFiltering for {PROJECT_NAME} project...")
    project_convs: dict[str, list[dict[str, Any]]] = {}
    for conv_id, messages in all_conversations.items():
        if is_project_conversation(messages):
            project_convs[conv_id] = messages

    print(f"Found {len(project_convs)} project conversations")

    # Analyze subagent usage
    print("\nAnalyzing subagent usage...")
    usage_data: dict[str, dict[str, Any]] = {}
    agent_totals: dict[str, int] = defaultdict(int)
    total_dispatches = 0
    parallel_count = 0
    score_sum = 0

    for conv_id, messages in project_convs.items():
        usage = analyze_subagent_usage(messages)
        score = calculate_usage_score(usage)

        usage_data[conv_id] = {
            'message_count': len(messages),
            'usage': usage,
            'score': score
        }

        # Aggregate stats
        for agent_type, count in usage['agent_mentions'].items():
            agent_totals[agent_type] += count
        total_dispatches += usage['dispatch_count']
        if usage['has_parallel_dispatch']:
            parallel_count += 1
        score_sum += score

    # Calculate summary statistics
    conv_count = len(project_convs)
    avg_score = score_sum / conv_count if conv_count > 0 else 0
    adoption_rate = sum(1 for d in usage_data.values() if d['score'] > 0) / conv_count * 100 if conv_count > 0 else 0

    stats = {
        'total_conversations': len(all_conversations),
        'project_conversations': conv_count,
        'total_dispatch_mentions': total_dispatches,
        'parallel_dispatch_conversations': parallel_count,
        'average_usage_score': round(avg_score, 1),
        'adoption_rate_percent': round(adoption_rate, 1),
        'agent_mention_totals': dict(agent_totals)
    }

    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)
    print(f"Total conversations: {stats['total_conversations']}")
    print(f"Project conversations: {stats['project_conversations']}")
    print(f"Subagent adoption rate: {stats['adoption_rate_percent']:.1f}%")
    print(f"Average usage score: {stats['average_usage_score']:.1f}/100")
    print(f"Total dispatch mentions: {stats['total_dispatch_mentions']}")
    print(f"Parallel dispatch conversations: {stats['parallel_dispatch_conversations']}")
    print("\nAgent mention totals:")
    for agent_type, count in sorted(stats['agent_mention_totals'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {agent_type}: {count}")

    # Top conversations by score
    print("\nTop 5 conversations by subagent usage:")
    sorted_usage = sorted(usage_data.items(), key=lambda x: x[1]['score'], reverse=True)[:5]
    for conv_id, data in sorted_usage:
        print(f"  {conv_id[:8]}... score={data['score']} agents={list(data['usage']['agent_mentions'].keys())}")

    conn.close()

    return usage_data, stats


if __name__ == "__main__":
    usage_data, stats = analyze_all_conversations()

    # Save results to JSON
    output_file = Path(__file__).parent.parent.parent.parent / DATA_DIR_NAME / OUTPUT_FILE_NAME
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Prepare serializable data
    serializable_data: dict[str, dict[str, Any]] = {}
    for conv_id, data in usage_data.items():
        serializable_data[conv_id] = {
            'message_count': data['message_count'],
            'score': data['score'],
            'agent_mentions': data['usage']['agent_mentions'],
            'dispatch_count': data['usage']['dispatch_count'],
            'has_parallel_dispatch': data['usage']['has_parallel_dispatch']
        }

    try:
        with open(output_file, 'w') as f:
            json.dump({
                'stats': stats,
                'conversations': serializable_data
            }, f, indent=2)
        print(f"\nResults saved to: {output_file}")
    except OSError as e:
        print(f"Error: Failed to write output file: {e}", file=sys.stderr)
        sys.exit(1)
