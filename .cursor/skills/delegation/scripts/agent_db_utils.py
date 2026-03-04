#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Shared database utilities for agent orchestration scripts.

Provides functions for accessing Cursor agent databases stored in
.cursor/chats/{project-hash}/{agent-uuid}/store.db

Each agent database contains:
- meta table: agentId, name, createdAt, latestRootBlobId
- blobs table: Full conversation history including prompts
"""

from __future__ import annotations

import json
import os
import platform
import getpass
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Constants
ENV_CHATS_PATH_KEY = "CURSOR_CHATS_PATH"
WSL_MOUNT_PREFIXES = ("/mnt/c", "/mnt/d", "/mnt/e", "/mnt/f")


@dataclass
class AgentMetadata:
    """Metadata for a Cursor agent."""

    agent_id: str
    name: str
    created_at: datetime
    latest_blob_id: str
    db_path: Path
    project_hash: str

    def __repr__(self) -> str:
        return f"Agent({self.name}, id={self.agent_id[:8]}..., created={self.created_at.isoformat()})"


@dataclass
class AgentPrompt:
    """Initial prompt/task for an agent."""

    agent_id: str
    prompt_text: str
    prompt_preview: str  # First 200 chars for catalog display


def _is_wsl() -> bool:
    """Return True when running under Windows Subsystem for Linux."""
    if platform.system() != "Linux":
        return False
    release = platform.release().lower()
    return "microsoft" in release or "wsl" in release


def _candidate_windows_usernames() -> list[str]:
    """Return candidate Windows usernames for WSL-mounted paths."""
    candidates = [
        os.environ.get("USERNAME"),
        os.environ.get("USER"),
        getpass.getuser(),
    ]
    return list(dict.fromkeys([name for name in candidates if name]))


def get_cursor_chats_path(user: str | None = None) -> Path | None:
    """
    Locate the Cursor chats directory.

    Checks in order:
    1. CURSOR_CHATS_PATH environment variable
    2. WSL Windows path
    3. Linux native path
    4. macOS path
    5. Windows path
    """
    # Check environment variable first
    if env_path := os.environ.get(ENV_CHATS_PATH_KEY):
        path = Path(env_path)
        if path.exists():
            return path

    system = platform.system()
    resolved_user = user or getpass.getuser()

    # WSL Windows path (Linux only)
    if _is_wsl():
        users_root = Path("/mnt/c/Users")
        if users_root.exists():
            for candidate_user in [resolved_user, *_candidate_windows_usernames()]:
                if not candidate_user:
                    continue
                wsl_path = users_root / candidate_user / ".cursor" / "chats"
                if wsl_path.exists():
                    return wsl_path

    if system == "Linux":
        linux_path = Path.home() / ".cursor" / "chats"
        if linux_path.exists():
            return linux_path

    if system == "Darwin":
        mac_path = Path.home() / ".cursor" / "chats"
        if mac_path.exists():
            return mac_path

    if system == "Windows":
        win_path = Path.home() / ".cursor" / "chats"
        if win_path.exists():
            return win_path

    return None


def _is_wsl_windows_path(path: Path) -> bool:
    """Check if path is on WSL Windows mount (requires immutable mode)."""
    path_str = str(path)
    return any(path_str.startswith(prefix) for prefix in WSL_MOUNT_PREFIXES)


def _decode_hex_value(hex_str: str) -> dict[str, Any] | None:
    """Decode a hex-encoded JSON value from SQLite."""
    try:
        decoded = bytes.fromhex(hex_str).decode("utf-8")
        return json.loads(decoded)
    except (ValueError, json.JSONDecodeError):
        return None


def load_agent_metadata(db_path: Path, project_hash: str) -> AgentMetadata | None:
    """Load metadata from an agent database."""
    if not db_path.exists():
        return None

    conn = None
    try:
        # Use immutable mode for WSL paths
        if _is_wsl_windows_path(db_path):
            uri = f"file:{db_path}?immutable=1"
            conn = sqlite3.connect(uri, uri=True)
        else:
            conn = sqlite3.connect(db_path)

        cursor = conn.cursor()
        cursor.execute("SELECT value FROM meta WHERE key = '0'")
        row = cursor.fetchone()

        if not row:
            return None

        # Value is hex-encoded JSON
        data = _decode_hex_value(row[0])
        if not data:
            return None

        # Parse timestamp (milliseconds since epoch)
        created_ts = data.get("createdAt", 0)
        created_dt = datetime.fromtimestamp(created_ts / 1000, tz=UTC).replace(tzinfo=None)

        return AgentMetadata(
            agent_id=data.get("agentId", ""),
            name=data.get("name", "Unknown"),
            created_at=created_dt,
            latest_blob_id=data.get("latestRootBlobId", ""),
            db_path=db_path,
            project_hash=project_hash,
        )
    except sqlite3.Error:
        return None
    finally:
        if conn is not None:
            conn.close()


def extract_agent_prompt(db_path: Path) -> AgentPrompt | None:
    """Extract the initial prompt from an agent's blob data."""
    if not db_path.exists():
        return None

    conn = None
    try:
        # Use immutable mode for WSL paths
        if _is_wsl_windows_path(db_path):
            uri = f"file:{db_path}?immutable=1"
            conn = sqlite3.connect(uri, uri=True)
        else:
            conn = sqlite3.connect(db_path)

        cursor = conn.cursor()

        # Get metadata first for agent_id
        cursor.execute("SELECT value FROM meta WHERE key = '0'")
        meta_row = cursor.fetchone()
        if not meta_row:
            return None

        meta_data = _decode_hex_value(meta_row[0])
        agent_id = meta_data.get("agentId", "") if meta_data else ""

        # Get all blobs and look for prompt content
        cursor.execute("SELECT hex(data) FROM blobs LIMIT 10")
        rows = cursor.fetchall()

        prompt_text = ""
        for row in rows:
            try:
                # Blobs are hex-encoded; decode and look for readable text
                decoded = bytes.fromhex(row[0]).decode("utf-8", errors="ignore")
                # Look for content that looks like a prompt (starts with @, contains task text)
                if decoded and len(decoded) > 20:
                    # Clean up binary artifacts
                    clean = "".join(c if c.isprintable() or c in "\n\t" else " " for c in decoded)
                    clean = " ".join(clean.split())  # Normalize whitespace
                    if clean and len(clean) > len(prompt_text):
                        prompt_text = clean
            except (ValueError, UnicodeDecodeError):
                continue

        if not prompt_text:
            return None

        return AgentPrompt(
            agent_id=agent_id,
            prompt_text=prompt_text,
            prompt_preview=prompt_text[:200] + "..." if len(prompt_text) > 200 else prompt_text,
        )
    except sqlite3.Error:
        return None
    finally:
        if conn is not None:
            conn.close()


def list_project_agents(chats_path: Path, project_hash: str) -> list[AgentMetadata]:
    """List all agents for a specific project."""
    project_dir = chats_path / project_hash
    if not project_dir.exists():
        return []

    agents = []
    for agent_dir in project_dir.iterdir():
        if not agent_dir.is_dir():
            continue

        db_path = agent_dir / "store.db"
        if not db_path.exists():
            continue

        metadata = load_agent_metadata(db_path, project_hash)
        if metadata:
            agents.append(metadata)

    # Sort by creation time, newest first
    agents.sort(key=lambda a: a.created_at, reverse=True)
    return agents


def list_all_projects(chats_path: Path) -> list[str]:
    """List all project hashes in the chats directory."""
    if not chats_path.exists():
        return []

    return [d.name for d in chats_path.iterdir() if d.is_dir() and len(d.name) == 32]


def find_project_by_name(chats_path: Path, project_name: str) -> str | None:
    """
    Find a project hash by searching agent prompts for the project name.

    This is a heuristic - looks for project name mentions in agent prompts.
    Returns the most likely project hash.
    """
    project_hashes = list_all_projects(chats_path)

    for project_hash in project_hashes:
        agents = list_project_agents(chats_path, project_hash)
        for agent in agents[:5]:  # Check first 5 agents
            prompt = extract_agent_prompt(agent.db_path)
            if prompt and project_name.lower() in prompt.prompt_text.lower():
                return project_hash

    return None
