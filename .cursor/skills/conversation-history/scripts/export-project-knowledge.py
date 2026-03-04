#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Description: Export structured knowledge base from project conversations
Usage: export-project-knowledge.py PROJECT_PATH FORMAT [OUTPUT_FILE]
"""

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import datetime
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
VALID_FORMATS = ['json', 'csv', 'markdown']
SAMPLE_TEXT_LIMIT = 500
SAMPLE_TEXT_PREVIEW = 200
MAX_FILES_TO_EXPORT = 50
MAX_CODE_PATTERNS_TO_EXPORT = 100
MAX_CODE_PATTERNS_CSV = 50
MAX_FILES_DISCUSSED = 20
MAX_SAMPLE_MESSAGES = 3
MAX_FILES_IN_CSV = 5


def export_project_knowledge(project_path: str, output_format: str, output_file: str | None = None) -> None:
    """Export structured knowledge base from conversations."""
    # Guard: Validate project path
    if not project_path:
        print("Error: Project path is required.", file=sys.stderr)
        sys.exit(2)

    # Guard: Validate output format
    if output_format not in VALID_FORMATS:
        print(f"Error: Invalid format '{output_format}'. Must be: {', '.join(VALID_FORMATS)}", file=sys.stderr)
        sys.exit(2)

    db_path = get_cursor_db_path()
    if not db_path:
        print("Error: Cursor database not found.", file=sys.stderr)
        print("Set CURSOR_DB_PATH environment variable to your database location:", file=sys.stderr)
        print("  Linux: ~/.config/Cursor/User/globalStorage/state.vscdb", file=sys.stderr)
        print(r"  Windows: C:\Users\<USERNAME>\AppData\Roaming\Cursor\User\globalStorage\state.vscdb", file=sys.stderr)
        print("  macOS: ~/Library/Application Support/Cursor/User/globalStorage/state.vscdb", file=sys.stderr)
        sys.exit(2)

    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        extension = 'md' if output_format == 'markdown' else output_format
        output_file = f"{project_path}_knowledge_{timestamp}.{extension}"

    print(f"Exporting knowledge for project: {project_path}")
    print(f"Output format: {output_format}")
    print(f"Output file: {output_file}")
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

    # Filter by project
    project_conversations = {}
    for conv_id, messages in all_conversations.items():
        if is_project_conversation(messages, project_path):
            project_conversations[conv_id] = messages

    print(f"Found {len(project_conversations)} project conversations")
    print("")

    # Extract data
    conversations_data: list[dict[str, Any]] = []
    code_patterns: list[dict[str, Any]] = []
    file_history = Counter()

    for conv_id, messages in project_conversations.items():
        conv_date = get_conversation_date(messages)
        files = find_files_in_conversation(messages)
        code_blocks = extract_code_blocks(messages)

        # Extract sample text
        sample_text = ""
        for msg in messages[:MAX_SAMPLE_MESSAGES]:
            data = msg.get('data', {})
            if data.get('text'):
                sample_text = data['text'][:SAMPLE_TEXT_LIMIT]
                break

        conversations_data.append({
            'id': conv_id,
            'date': conv_date.isoformat() if conv_date else None,
            'message_count': len(messages),
            'files': list(files),
            'sample_text': sample_text
        })

        # Track files
        for file_path in files:
            file_history[file_path] += 1

        # Extract code patterns
        for cb in code_blocks:
            code_patterns.append({
                'conversation_id': conv_id,
                'language': cb['language'],
                'line_count': cb['line_count'],
                'code': cb['code'][:SAMPLE_TEXT_LIMIT]  # Truncate for export
            })

    # Prepare export data
    export_data: dict[str, Any] = {
        'project': project_path,
        'generated': datetime.now().isoformat(),
        'total_conversations': len(conversations_data),
        'conversations': conversations_data,
        'file_history': dict(file_history.most_common(MAX_FILES_TO_EXPORT)),
        'code_patterns': code_patterns[:MAX_CODE_PATTERNS_TO_EXPORT]  # Limit for export
    }

    # Export based on format
    output_path = Path(output_file)

    def _export_json() -> None:
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)

    def _export_csv() -> None:
        # Write conversations
        conv_file = output_path.parent / f"{output_path.stem}_conversations.csv"
        with open(conv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'date', 'message_count', 'files', 'sample_text'])
            for conv in conversations_data:
                writer.writerow([
                    conv['id'],
                    conv['date'] or '',
                    conv['message_count'],
                    '; '.join(conv['files'][:MAX_FILES_IN_CSV]),
                    conv['sample_text'][:SAMPLE_TEXT_PREVIEW]
                ])

        # Write files
        files_file = output_path.parent / f"{output_path.stem}_files.csv"
        with open(files_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['filename', 'discussion_count'])
            for file_path, count in file_history.most_common():
                writer.writerow([file_path, count])

        # Write patterns
        patterns_file = output_path.parent / f"{output_path.stem}_patterns.csv"
        with open(patterns_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['conversation_id', 'language', 'line_count', 'code_preview'])
            for pattern in code_patterns[:MAX_CODE_PATTERNS_CSV]:
                writer.writerow([
                    pattern['conversation_id'],
                    pattern['language'],
                    pattern['line_count'],
                    pattern['code'][:SAMPLE_TEXT_PREVIEW]
                ])

        print("Exported CSV files:")
        print(f"  - {conv_file}")
        print(f"  - {files_file}")
        print(f"  - {patterns_file}")

    def _export_markdown() -> None:
        with open(output_path, 'w') as f:
            f.write(f"# {project_path} Knowledge Base\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write("## Overview\n\n")
            f.write(f"- Total conversations: {len(conversations_data)}\n")
            f.write(f"- Total files discussed: {len(file_history)}\n")
            f.write(f"- Total code patterns: {len(code_patterns)}\n\n")

            f.write("## File History\n\n")
            f.write("Most discussed files:\n\n")
            for file_path, count in file_history.most_common(MAX_FILES_DISCUSSED):
                f.write(f"- `{file_path}`: {count} discussions\n")
            f.write("\n")

            f.write("## Code Patterns\n\n")
            code_preview_limit = 300
            for i, pattern in enumerate(code_patterns[:MAX_FILES_DISCUSSED], 1):
                f.write(f"### Pattern {i}\n\n")
                f.write(f"**Language**: {pattern['language']}  \n")
                f.write(f"**Lines**: {pattern['line_count']}  \n")
                f.write(f"**Conversation**: {pattern['conversation_id'][:8]}...\n\n")
                f.write("```\n")
                f.write(pattern['code'][:code_preview_limit])
                f.write("\n```\n\n")
    format_handlers = {
        'json': _export_json,
        'csv': _export_csv,
        'markdown': _export_markdown,
    }
    format_handlers[output_format]()

    print(f"\nKnowledge base exported to: {output_path}")


if __name__ == '__main__':
    # Guard: Validate arguments
    parser = argparse.ArgumentParser(
        description="Export structured knowledge base from project conversations."
    )
    parser.add_argument("project_path", help="Project path/name to filter conversations")
    parser.add_argument(
        "format",
        choices=VALID_FORMATS,
        help="Output format for exported knowledge base",
    )
    parser.add_argument(
        "output_file",
        nargs="?",
        default=None,
        help="Optional output file path (default: auto-generated with timestamp)",
    )

    args = parser.parse_args()

    project = args.project_path
    fmt = args.format.lower()
    output = args.output_file

    export_project_knowledge(project, fmt, output)
