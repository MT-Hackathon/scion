#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Build a persistent agent catalog for cross-thread memory retrieval.

Creates a markdown catalog file that maps agent IDs to their domains/topics.
This catalog enables cross-thread memory retrieval by documenting which
agents know about which topics.

Usage:
    uv run build_agent_catalog.py PROJECT_HASH                      # Build catalog
    uv run build_agent_catalog.py PROJECT_HASH --output catalog.md  # Custom output
    uv run build_agent_catalog.py PROJECT_HASH --limit 50           # More agents

Output:
    Writes to .cursor/handoffs/agent-catalog.md by default.
    Format is markdown with agent IDs, dates, and topic summaries.

Use Case:
    After context summarization or in a new thread, consult the catalog
    to find agents that worked on specific domains, then resume them.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

from agent_db_utils import (
    extract_agent_prompt,
    get_cursor_chats_path,
    list_project_agents,
)

DEFAULT_LIMIT = 30
DEFAULT_OUTPUT = ".cursor/handoffs/agent-catalog.md"


def _display_chats_error() -> None:
    """Display help when chats directory cannot be found."""
    print("Error: Cursor chats directory not found.")
    print("Set CURSOR_CHATS_PATH to your .cursor/chats path.")


def _extract_topic_summary(prompt_text: str, max_length: int = 150) -> str:
    """Extract a clean topic summary from raw prompt text."""
    # Clean up binary artifacts and normalize
    clean = "".join(c if c.isprintable() or c in "\n\t" else " " for c in prompt_text)
    clean = " ".join(clean.split())

    # Try to find meaningful content
    # Look for file references as topic indicators
    if "@" in clean:
        parts = clean.split("@")
        if len(parts) > 1:
            # Get the part after @ that looks like a path
            for part in parts[1:]:
                if "/" in part or "." in part:
                    file_ref = part.split()[0] if part.split() else part
                    return f"Working on: {file_ref[:80]}"

    # Otherwise just use the start of the prompt
    if len(clean) > max_length:
        return clean[:max_length] + "..."
    return clean


def build_catalog_command(
    project_hash: str,
    output_path: str = DEFAULT_OUTPUT,
    limit: int = DEFAULT_LIMIT,
) -> int:
    """Build the agent catalog."""
    chats_path = get_cursor_chats_path()
    if not chats_path:
        _display_chats_error()
        return 1

    agents = list_project_agents(chats_path, project_hash)

    if not agents:
        print(f"No agents found for project {project_hash}")
        return 0

    agents = agents[:limit]

    # Build catalog content
    lines = [
        "# Agent Catalog",
        "",
        f"Generated: {datetime.now().isoformat()}",
        f"Project: {project_hash}",
        f"Agents: {len(agents)}",
        "",
        "## How to Use",
        "",
        "To resume an agent for a briefing:",
        "",
        "```",
        'Task tool with resume="<agent_id>" and prompt="Brief me on what we worked on"',
        "```",
        "",
        "## Agent Registry",
        "",
        "| Date | Agent ID | Topic |",
        "|------|----------|-------|",
    ]

    for agent in agents:
        date_str = agent.created_at.strftime("%Y-%m-%d")
        agent_id_short = agent.agent_id[:12]

        # Get topic from prompt
        prompt = extract_agent_prompt(agent.db_path)
        topic = _extract_topic_summary(prompt.prompt_text) if prompt else "Unknown"

        # Escape pipes for markdown table
        topic = topic.replace("|", "\\|")

        lines.append(f"| {date_str} | `{agent_id_short}...` | {topic} |")

    # Add full ID reference section
    lines.extend([
        "",
        "## Full Agent IDs (for resume)",
        "",
        "```",
    ])

    for agent in agents:
        date_str = agent.created_at.strftime("%Y-%m-%d")
        prompt = extract_agent_prompt(agent.db_path)
        topic = _extract_topic_summary(prompt.prompt_text, 60) if prompt else "Unknown"
        lines.append(f"# {date_str}: {topic[:50]}...")
        lines.append(agent.agent_id)
        lines.append("")

    lines.append("```")

    # Write output
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines))

    print(f"Catalog written to {output_path}")
    print(f"Contains {len(agents)} agents from project {project_hash[:12]}...")

    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="Build a persistent agent catalog for cross-thread memory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "project_hash",
        help="Project hash (32-character hex string)",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help=f"Output file path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"Maximum agents to catalog (default: {DEFAULT_LIMIT})",
    )

    args = parser.parse_args(argv)

    return build_catalog_command(
        args.project_hash,
        output_path=args.output,
        limit=args.limit,
    )


if __name__ == "__main__":
    sys.exit(main())
