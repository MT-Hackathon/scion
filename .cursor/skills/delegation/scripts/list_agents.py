#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
List Cursor agents for a project with their topics/prompts.

Scans agent databases and outputs a catalog of agents with:
- Agent ID (for resume)
- Name
- Creation date
- Initial prompt preview (helps identify what the agent knows)

Usage:
    uv run list_agents.py PROJECT_HASH                    # List agents for project
    uv run list_agents.py PROJECT_HASH --limit 10         # Limit results
    uv run list_agents.py PROJECT_HASH --with-prompts     # Include full prompts
    uv run list_agents.py PROJECT_HASH --json             # JSON output
    uv run list_agents.py --list-projects                 # List all project hashes
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

from agent_db_utils import (
    AgentMetadata,
    extract_agent_prompt,
    get_cursor_chats_path,
    list_all_projects,
    list_project_agents,
)

DEFAULT_LIMIT = 20


def _display_chats_error() -> None:
    """Display help when chats directory cannot be found."""
    print("Error: Cursor chats directory not found.")
    print("Set CURSOR_CHATS_PATH to your .cursor/chats path.")
    print("  Linux/macOS: ~/.cursor/chats")
    print(r"  Windows: C:\Users\<USER>\.cursor\chats")


def _format_agent_line(agent: AgentMetadata, prompt_preview: str | None = None) -> str:
    """Format a single agent for display."""
    date_str = agent.created_at.strftime("%Y-%m-%d %H:%M")
    line = f"  {agent.agent_id[:12]}  {date_str}  {agent.name}"
    if prompt_preview:
        # Truncate and clean for display
        preview = prompt_preview[:80].replace("\n", " ")
        line += f"\n    └─ {preview}..."
    return line


def list_projects_command() -> int:
    """List all project hashes."""
    chats_path = get_cursor_chats_path()
    if not chats_path:
        _display_chats_error()
        return 1

    print(f"Chats directory: {chats_path}\n")
    projects = list_all_projects(chats_path)

    if not projects:
        print("No projects found.")
        return 0

    print(f"Found {len(projects)} projects:\n")
    for project_hash in projects:
        agents = list_project_agents(chats_path, project_hash)
        print(f"  {project_hash}  ({len(agents)} agents)")

    return 0


def list_agents_command(
    project_hash: str,
    limit: int = DEFAULT_LIMIT,
    with_prompts: bool = False,
    as_json: bool = False,
) -> int:
    """List agents for a project."""
    chats_path = get_cursor_chats_path()
    if not chats_path:
        _display_chats_error()
        return 1

    agents = list_project_agents(chats_path, project_hash)

    if not agents:
        print(f"No agents found for project {project_hash}")
        return 0

    # Apply limit
    agents = agents[:limit]

    if as_json:
        output = []
        for agent in agents:
            agent_data = {
                "agent_id": agent.agent_id,
                "name": agent.name,
                "created_at": agent.created_at.isoformat(),
                "db_path": str(agent.db_path),
            }
            if with_prompts:
                prompt = extract_agent_prompt(agent.db_path)
                agent_data["prompt"] = prompt.prompt_text if prompt else None
            output.append(agent_data)
        print(json.dumps(output, indent=2))
        return 0

    # Text output
    print(f"Agents for project {project_hash[:12]}...")
    print(f"Found {len(agents)} agents (showing {min(limit, len(agents))})\n")
    print("-" * 80)

    for agent in agents:
        prompt_preview = None
        if with_prompts:
            prompt = extract_agent_prompt(agent.db_path)
            prompt_preview = prompt.prompt_preview if prompt else None

        print(_format_agent_line(agent, prompt_preview))

    print("-" * 80)
    print(f"\nTo resume an agent: Task tool with resume=<agent_id>")

    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="List Cursor agents for a project",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "project_hash",
        nargs="?",
        help="Project hash (32-character hex string)",
    )
    parser.add_argument(
        "--list-projects",
        action="store_true",
        help="List all project hashes instead of agents",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"Maximum agents to display (default: {DEFAULT_LIMIT})",
    )
    parser.add_argument(
        "--with-prompts",
        action="store_true",
        help="Include initial prompt preview for each agent",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )

    args = parser.parse_args(argv)

    if args.list_projects:
        return list_projects_command()

    if not args.project_hash:
        parser.error("project_hash is required (or use --list-projects)")

    return list_agents_command(
        args.project_hash,
        limit=args.limit,
        with_prompts=args.with_prompts,
        as_json=args.json,
    )


if __name__ == "__main__":
    sys.exit(main())
