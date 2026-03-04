#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Shared database utilities for chat history scripts.
Provides common functions for accessing Cursor conversation database.
"""

import fnmatch
import getpass
import json
import os
import platform
import re
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

# Constants
ENV_DB_PATH_KEY = 'CURSOR_DB_PATH'
BUBBLE_KEY_PREFIX = 'bubbleId:'
MIN_KEY_PARTS = 2
DEFAULT_TIMESTAMP_FIELDS = ['timestamp', 'createdAt', 'date', 'time']
TIMESTAMP_FORMATS = ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d', '%Y-%m-%d %H:%M:%S']
CODE_BLOCK_PATTERN = r'```(\w+)?\n(.*?)```'
WSL_MOUNT_PREFIXES = ('/mnt/c', '/mnt/d', '/mnt/e', '/mnt/f')


def _get_env_db_path() -> Path | None:
    """Get database path from environment variable if set and exists."""
    db_path = os.environ.get(ENV_DB_PATH_KEY)
    if not db_path:
        return None
    path = Path(db_path).expanduser()
    if not path.exists():
        return None
    return path


def _is_wsl() -> bool:
    """Return True when running under Windows Subsystem for Linux."""
    if platform.system() != 'Linux':
        return False
    release = platform.release().lower()
    return 'microsoft' in release or 'wsl' in release


def _candidate_windows_usernames() -> list[str]:
    """Return candidate Windows usernames for WSL-mounted paths."""
    candidates = [
        os.environ.get('USERNAME'),
        os.environ.get('USER'),
        getpass.getuser(),
    ]
    # Preserve order while removing empty/duplicate values
    return list(dict.fromkeys([name for name in candidates if name]))


def _get_wsl_windows_path() -> Path | None:
    """Get WSL Windows path for Cursor database."""
    mount_root = Path('/mnt/c/Users')
    if not mount_root.exists():
        return None

    for user in _candidate_windows_usernames():
        windows_path = (
            mount_root
            / user
            / 'AppData'
            / 'Roaming'
            / 'Cursor'
            / 'User'
            / 'globalStorage'
            / 'state.vscdb'
        )
        if windows_path.exists():
            return windows_path
    return None


def _get_linux_native_path() -> Path | None:
    """Get Linux native path for Cursor database."""
    linux_path = Path.home() / ".config" / "Cursor" / "User" / "globalStorage" / "state.vscdb"
    if not linux_path.exists():
        return None
    return linux_path


def _get_mac_path() -> Path | None:
    """Get macOS path for Cursor database."""
    mac_path = Path.home() / "Library" / "Application Support" / "Cursor" / "User" / "globalStorage" / "state.vscdb"
    if not mac_path.exists():
        return None
    return mac_path


def _get_windows_path() -> Path | None:
    """Get Windows path for Cursor database."""
    appdata = os.environ.get('APPDATA')
    if appdata:
        roaming_base = Path(appdata)
    else:
        roaming_base = Path.home() / 'AppData' / 'Roaming'
    windows_path = roaming_base / 'Cursor' / 'User' / 'globalStorage' / 'state.vscdb'
    if not windows_path.exists():
        return None
    return windows_path


def _is_wsl_windows_path(db_path: str | Path) -> bool:
    """Check if path is on WSL Windows mount (requires immutable mode for SQLite).

    WSL2's 9p filesystem (DrvFs) doesn't fully support POSIX file locking,
    which causes SQLite disk I/O errors when Cursor has the database open
    with WAL mode. Using immutable URI mode bypasses these issues.
    """
    # Guard: Validate input
    if not db_path:
        return False

    db_path_str = str(db_path)
    # Check if path starts with any WSL mount prefix
    return any(db_path_str.startswith(prefix) for prefix in WSL_MOUNT_PREFIXES)


def get_cursor_db_path() -> str:
    """Detect Cursor database path based on platform and environment."""
    # Guard: Check environment variable first
    env_path = _get_env_db_path()
    if env_path:
        return str(env_path)

    # Guard: Get system and user info
    system = platform.system()
    if not system:
        return os.environ.get(ENV_DB_PATH_KEY, '')

    def _linux_path() -> Path | None:
        """Resolve Linux path, preferring WSL mounted Windows DB when available."""
        if _is_wsl():
            wsl_path = _get_wsl_windows_path()
            if wsl_path:
                return wsl_path
        return _get_linux_native_path()

    platform_path_handlers = {
        'Linux': _linux_path,
        'Darwin': _get_mac_path,
        'Windows': _get_windows_path,
    }
    path_handler = platform_path_handlers.get(system)
    if path_handler:
        platform_path = path_handler()
        if platform_path:
            return str(platform_path)

    # Fallback to environment variable even if doesn't exist (let caller handle error)
    return os.environ.get(ENV_DB_PATH_KEY, '')


def load_database(db_path: str | None = None) -> sqlite3.Connection:
    """Connect to Cursor database.

    For WSL Windows paths, uses SQLite immutable URI mode to bypass WAL
    file locking issues that cause disk I/O errors on 9p filesystem.
    """
    # Guard: Get db_path if not provided
    if db_path is None:
        db_path = get_cursor_db_path()

    # Guard: Validate db_path is set
    if not db_path:
        raise FileNotFoundError(
            "Cursor database not found. Set CURSOR_DB_PATH environment variable "
            "or ensure Cursor is installed in the default location."
        )

    # Guard: Validate db_path exists
    db_file = Path(db_path)
    if not db_file.exists():
        raise FileNotFoundError(
            f"Cursor database not found at {db_path}. "
            "Set CURSOR_DB_PATH environment variable to correct location."
        )

    # Use immutable URI mode for WSL Windows paths to avoid WAL conflicts
    # This opens read-only but bypasses file locking issues with 9p filesystem
    if _is_wsl_windows_path(db_path):
        uri = f'file:{db_file}?immutable=1'
        return sqlite3.connect(uri, uri=True)

    return sqlite3.connect(db_file)


def _parse_bubble_key(key: str) -> tuple[str, str | None] | None:
    """Parse bubble key into conversation_id and message_id."""
    # Guard: Validate key format
    if not key or not key.startswith(BUBBLE_KEY_PREFIX):
        return None

    parts = key.split(':')
    # Guard: Validate minimum parts
    if len(parts) < MIN_KEY_PARTS:
        return None

    conv_id = parts[1]
    message_id = parts[2] if len(parts) > 2 else None
    return (conv_id, message_id)


def _parse_bubble_value(value: Any) -> dict[str, Any] | None:
    """Parse bubble value JSON into dictionary."""
    # Guard: Handle None value
    if value is None:
        return None

    try:
        if isinstance(value, bytes):
            data = json.loads(value.decode('utf-8', errors='ignore'))
        else:
            data = json.loads(value)
        return data
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    except Exception:
        return None


def extract_conversations(conn: sqlite3.Connection) -> dict[str, list[dict[str, Any]]]:
    """Extract all conversations from database."""
    # Guard: Validate connection
    if conn is None:
        raise ValueError("Database connection is None")

    cursor = conn.cursor()

    # Get all bubble entries
    cursor.execute(f"SELECT key, value FROM cursorDiskKV WHERE key LIKE '{BUBBLE_KEY_PREFIX}%'")

    conversations: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for key, value in cursor.fetchall():
        # Parse key
        key_result = _parse_bubble_key(key)
        if not key_result:
            continue

        conv_id, message_id = key_result

        # Parse value
        data = _parse_bubble_value(value)
        if data is None:
            continue

        conversations[conv_id].append({
            'message_id': message_id,
            'data': data,
            'key': key
        })

    return conversations


def _normalize_project_patterns(project_path: str) -> list[str]:
    """Normalize project path into search patterns."""
    # Guard: Validate project_path
    if not project_path:
        return []

    base_lower = project_path.lower()
    return [
        base_lower,
        base_lower.replace('-', '_'),
        base_lower.replace('_', '-')
    ]


def _check_field_for_patterns(field_value: Any, patterns: list[str]) -> bool:
    """Check if field value contains any project pattern."""
    # Guard: Validate inputs
    if not field_value or not patterns:
        return False

    field_str = str(field_value).lower()
    return any(pattern in field_str for pattern in patterns)


def is_project_conversation(conv_messages: list[dict[str, Any]], project_path: str) -> bool:
    """Check if conversation is related to project."""
    # Guard: Validate inputs
    if not conv_messages or not project_path:
        return False

    project_patterns = _normalize_project_patterns(project_path)
    # Guard: Ensure we have patterns
    if not project_patterns:
        return False

    for msg in conv_messages:
        # Guard: Validate message structure
        if not isinstance(msg, dict) or 'data' not in msg:
            continue

        data = msg['data']
        if not isinstance(data, dict):
            continue

        # Check relevantFiles
        if data.get('relevantFiles'):
            for file_path in data['relevantFiles']:
                if _check_field_for_patterns(file_path, project_patterns):
                    return True

        # Check attachedFolders
        for folder_field in ['attachedFolders', 'attachedFoldersNew']:
            if data.get(folder_field):
                for folder in data[folder_field]:
                    if _check_field_for_patterns(folder, project_patterns):
                        return True

        # Check text content for project references
        if data.get('text') and _check_field_for_patterns(data['text'], project_patterns):
            return True

        # Check codebaseContextChunks
        if data.get('codebaseContextChunks'):
            for chunk in data['codebaseContextChunks']:
                chunk_str = json.dumps(chunk).lower()
                if any(pattern in chunk_str for pattern in project_patterns):
                    return True

    return False


def search_text_in_conversation(conv_messages: list[dict[str, Any]], search_term: str) -> bool:
    """Search for term in conversation messages."""
    # Guard: Validate inputs
    if not conv_messages or not search_term:
        return False

    search_lower = search_term.lower()

    for msg in conv_messages:
        # Guard: Validate message structure
        if not isinstance(msg, dict) or 'data' not in msg:
            continue

        data = msg['data']
        if not isinstance(data, dict):
            continue

        # Search in text
        if data.get('text') and search_lower in str(data['text']).lower():
            return True

        # Search in richText
        if data.get('richText'):
            rich_text_str = str(data['richText']).lower()
            if search_lower in rich_text_str:
                return True

        # Search in code blocks
        if 'codeblocks' in data and isinstance(data['codeblocks'], list):
            for codeblock in data['codeblocks']:
                code_str = json.dumps(codeblock).lower()
                if search_lower in code_str:
                    return True

    return False


def file_matches_pattern(file_path: str, pattern: str) -> bool:
    """Check if file path matches pattern (supports wildcards)."""
    # Guard: Validate inputs
    if not file_path or not pattern:
        return False

    return fnmatch.fnmatch(file_path.lower(), pattern.lower())


def find_files_in_conversation(conv_messages: list[dict[str, Any]]) -> set[str]:
    """Extract all file references from conversation."""
    # Guard: Validate input
    if not conv_messages:
        return set()

    files: set[str] = set()

    for msg in conv_messages:
        # Guard: Validate message structure
        if not isinstance(msg, dict) or 'data' not in msg:
            continue

        data = msg['data']
        if not isinstance(data, dict):
            continue

        # Check relevantFiles
        if 'relevantFiles' in data and isinstance(data['relevantFiles'], list):
            for file_path in data['relevantFiles']:
                if isinstance(file_path, str):
                    files.add(file_path)

        # Check codebaseContextChunks for file references
        if 'codebaseContextChunks' in data and isinstance(data['codebaseContextChunks'], list):
            for chunk in data['codebaseContextChunks']:
                if isinstance(chunk, dict):
                    # Look for file paths in chunk
                    if 'file' in chunk:
                        files.add(str(chunk['file']))
                    if 'path' in chunk:
                        files.add(str(chunk['path']))

    return files


def _extract_markdown_code_blocks(
    text: str,
    language_filter: str | None,
    min_length: int,
    message_id: str | None
) -> list[dict[str, Any]]:
    """Extract code blocks from markdown text."""
    # Guard: Validate input
    if not text:
        return []

    code_blocks: list[dict[str, Any]] = []
    matches = re.findall(CODE_BLOCK_PATTERN, text, re.DOTALL)

    for lang, code in matches:
        # Guard: Apply language filter
        if language_filter and lang.lower() != language_filter.lower():
            continue

        lines = code.split('\n')
        # Guard: Apply minimum length filter
        if len(lines) < min_length:
            continue

        code_blocks.append({
            'language': lang or 'unknown',
            'code': code,
            'line_count': len(lines),
            'message_id': message_id
        })

    return code_blocks


def _extract_structured_code_blocks(
    codeblocks: list[dict[str, Any]],
    language_filter: str | None,
    min_length: int,
    message_id: str | None
) -> list[dict[str, Any]]:
    """Extract code blocks from structured codeblocks field."""
    # Guard: Validate input
    if not codeblocks:
        return []

    code_blocks: list[dict[str, Any]] = []

    for codeblock in codeblocks:
        # Guard: Validate codeblock structure
        if not isinstance(codeblock, dict):
            continue

        cb_lang = codeblock.get('language', 'unknown')
        cb_code = codeblock.get('code', '')

        # Guard: Apply language filter
        if language_filter and cb_lang.lower() != language_filter.lower():
            continue

        lines = cb_code.split('\n')
        # Guard: Apply minimum length filter
        if len(lines) < min_length:
            continue

        code_blocks.append({
            'language': cb_lang,
            'code': cb_code,
            'line_count': len(lines),
            'message_id': message_id
        })

    return code_blocks


def extract_code_blocks(
    conv_messages: list[dict[str, Any]],
    language: str | None = None,
    min_length: int = 0
) -> list[dict[str, Any]]:
    """Extract code blocks from conversation."""
    # Guard: Validate input
    if not conv_messages:
        return []

    # Guard: Validate min_length
    if min_length < 0:
        min_length = 0

    code_blocks: list[dict[str, Any]] = []

    for msg in conv_messages:
        # Guard: Validate message structure
        if not isinstance(msg, dict) or 'data' not in msg:
            continue

        data = msg['data']
        if not isinstance(data, dict):
            continue

        message_id = msg.get('message_id')

        # Look for code in text (markdown code blocks)
        if data.get('text'):
            text_blocks = _extract_markdown_code_blocks(
                str(data['text']),
                language,
                min_length,
                message_id
            )
            code_blocks.extend(text_blocks)

        # Check for structured codeblocks
        if 'codeblocks' in data and isinstance(data['codeblocks'], list):
            structured_blocks = _extract_structured_code_blocks(
                data['codeblocks'],
                language,
                min_length,
                message_id
            )
            code_blocks.extend(structured_blocks)

    return code_blocks


def _parse_timestamp_value(ts: Any) -> datetime | None:
    """Parse timestamp value into datetime object."""
    # Guard: Handle None
    if ts is None:
        return None

    try:
        # Handle numeric timestamps
        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(ts)

        # Handle string timestamps
        if isinstance(ts, str):
            for fmt in TIMESTAMP_FORMATS:
                try:
                    return datetime.strptime(ts, fmt)
                except ValueError:
                    continue

        return None
    except (ValueError, OSError, OverflowError):
        return None


def get_conversation_date(conv_messages: list[dict[str, Any]]) -> datetime | None:
    """Extract date from conversation (from first message)."""
    # Guard: Validate input
    if not conv_messages:
        return None

    # Guard: Validate first message structure
    first_msg = conv_messages[0]
    if not isinstance(first_msg, dict):
        return None

    data = first_msg.get('data', {})
    if not isinstance(data, dict):
        return None

    # Look for timestamp fields
    for field in DEFAULT_TIMESTAMP_FIELDS:
        if field not in data:
            continue

        timestamp = _parse_timestamp_value(data[field])
        if timestamp:
            return timestamp

    return None
