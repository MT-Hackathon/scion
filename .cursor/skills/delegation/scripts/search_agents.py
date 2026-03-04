#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Search Cursor agents by topic/prompt content.

Searches agent prompt history for keywords to find agents that worked on
specific topics. Returns agent IDs suitable for resume.

Usage:
    uv run search_agents.py PROJECT_HASH "entity config"     # Search by topic
    uv run search_agents.py PROJECT_HASH "accessibility"     # Find accessibility work
    uv run search_agents.py PROJECT_HASH "GitLab" --limit 5  # Limit results
    uv run search_agents.py PROJECT_HASH "auth" --json       # JSON output

Use Case:
    After context window summarization, search for agents that worked on
    a specific domain, then resume them to recover the execution context.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

from agent_db_utils import (
    extract_agent_prompt,
    get_cursor_chats_path,
    list_project_agents,
)

DEFAULT_LIMIT = 10


def _display_chats_error() -> None:
    """Display help when chats directory cannot be found."""
    print("Error: Cursor chats directory not found.")
    print("Set CURSOR_CHATS_PATH to your .cursor/chats path.")


def search_agents_command(
    project_hash: str,
    query: str,
    limit: int = DEFAULT_LIMIT,
    as_json: bool = False,
) -> int:
    """Search agents by prompt content."""
    chats_path = get_cursor_chats_path()
    if not chats_path:
        _display_chats_error()
        return 1

    agents = list_project_agents(chats_path, project_hash)

    if not agents:
        print(f"No agents found for project {project_hash}")
        return 0

    # Search prompts for query
    query_lower = query.lower()
    matches = []

    for agent in agents:
        prompt = extract_agent_prompt(agent.db_path)
        if not prompt:
            continue

        if query_lower in prompt.prompt_text.lower():
            # Calculate relevance (simple: count occurrences)
            relevance = prompt.prompt_text.lower().count(query_lower)
            matches.append({
                "agent": agent,
                "prompt": prompt,
                "relevance": relevance,
            })

    # Sort by relevance
    matches.sort(key=lambda m: m["relevance"], reverse=True)
    matches = matches[:limit]

    if not matches:
        print(f"No agents found matching '{query}'")
        return 0

    if as_json:
        output = []
        for match in matches:
            output.append({
                "agent_id": match["agent"].agent_id,
                "name": match["agent"].name,
                "created_at": match["agent"].created_at.isoformat(),
                "relevance": match["relevance"],
                "prompt_preview": match["prompt"].prompt_preview,
            })
        print(json.dumps(output, indent=2))
        return 0

    # Text output
    print(f"Search results for '{query}' in project {project_hash[:12]}...")
    print(f"Found {len(matches)} matching agents\n")
    print("-" * 80)

    for match in matches:
        agent = match["agent"]
        prompt = match["prompt"]
        date_str = agent.created_at.strftime("%Y-%m-%d %H:%M")

        print(f"  {agent.agent_id}")
        print(f"    Created: {date_str}  Relevance: {match['relevance']}")

        # Show context around the match
        prompt_lower = prompt.prompt_text.lower()
        idx = prompt_lower.find(query_lower)
        if idx >= 0:
            start = max(0, idx - 50)
            end = min(len(prompt.prompt_text), idx + len(query) + 100)
            context = prompt.prompt_text[start:end].replace("\n", " ")
            print(f"    ...{context}...")
        print()

    print("-" * 80)
    print("\nTo resume an agent:")
    print("  Task tool with resume=<agent_id>")
    print("\nExample prompt after resume:")
    print('  "Brief me on what we worked on together"')

    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="Search Cursor agents by topic/prompt content",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "project_hash",
        help="Project hash (32-character hex string)",
    )
    parser.add_argument(
        "query",
        help="Search query (case-insensitive)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"Maximum results (default: {DEFAULT_LIMIT})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )

    args = parser.parse_args(argv)

    return search_agents_command(
        args.project_hash,
        args.query,
        limit=args.limit,
        as_json=args.json,
    )


if __name__ == "__main__":
    sys.exit(main())
