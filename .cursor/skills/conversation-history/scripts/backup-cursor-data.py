#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Comprehensive backup of Cursor data including chat history, settings, and config files.

Usage:
  backup-cursor-data.py                    # Backup to default location
  backup-cursor-data.py --output-dir DIR   # Backup to specific directory
  backup-cursor-data.py --dry-run          # Show what would be backed up
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import platform
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Constants
DB_FILENAME = 'state.vscdb'
GLOBAL_STORAGE_SUBPATH = 'Cursor/User/globalStorage'
USER_SUBPATH = 'Cursor/User'
TIMEOUT_SECONDS = 30
WSL_MOUNT_PREFIXES = ('/mnt/c', '/mnt/d', '/mnt/e', '/mnt/f')


def _is_wsl() -> bool:
    """Return True when running in Windows Subsystem for Linux."""
    if platform.system() != 'Linux':
        return False
    release = platform.release().lower()
    return 'microsoft' in release or 'wsl' in release


def _candidate_windows_usernames() -> list[str]:
    """Return candidate usernames for WSL Windows-mounted paths."""
    candidates = [
        os.environ.get('USERNAME'),
        os.environ.get('USER'),
        getpass.getuser(),
    ]
    return list(dict.fromkeys([name for name in candidates if name]))


def _resolve_windows_roaming_base() -> Path:
    """Resolve AppData/Roaming base path on native Windows."""
    appdata = os.environ.get('APPDATA')
    if appdata:
        return Path(appdata)
    return Path.home() / 'AppData' / 'Roaming'


def _connect_database(db_path: Path) -> sqlite3.Connection:
    """Connect to SQLite database, using immutable mode for WSL Windows paths.

    WSL2's 9p filesystem doesn't support POSIX file locking, which causes
    SQLite disk I/O errors when Cursor has the database open with WAL mode.
    Using immutable URI mode bypasses these issues (read-only access).
    """
    path_str = str(db_path)
    if any(path_str.startswith(prefix) for prefix in WSL_MOUNT_PREFIXES):
        uri = f'file:{path_str}?immutable=1'
        return sqlite3.connect(uri, uri=True, timeout=TIMEOUT_SECONDS)
    return sqlite3.connect(path_str, timeout=TIMEOUT_SECONDS)

# Files to backup from User directory
CONFIG_FILES = ['settings.json', 'keybindings.json']
CONFIG_DIRS = ['snippets']

# ItemTable keys that contain important settings (not conversation-specific)
SETTINGS_KEY_PREFIXES = [
    'cursor/',
    'cursorAuth/',
    'cursorai/',
    'anysphere.',
    'workbench.',
    'editor.',
    'terminal.',
]


def _get_cursor_directories() -> tuple[Path | None, Path | None]:
    """Find Cursor globalStorage and User directories."""
    system = platform.system()

    if system == 'Windows':
        base = _resolve_windows_roaming_base()
        global_storage = base / GLOBAL_STORAGE_SUBPATH
        user_dir = base / USER_SUBPATH
        if global_storage.exists():
            return global_storage, user_dir

    if system == 'Linux':
        if _is_wsl():
            users_root = Path('/mnt/c/Users')
            if users_root.exists():
                for user in _candidate_windows_usernames():
                    base = users_root / user / 'AppData' / 'Roaming'
                    global_storage = base / GLOBAL_STORAGE_SUBPATH
                    user_dir = base / USER_SUBPATH
                    if global_storage.exists():
                        return global_storage, user_dir

        linux_base = Path.home() / '.config'
        global_storage = linux_base / GLOBAL_STORAGE_SUBPATH
        user_dir = linux_base / USER_SUBPATH
        if global_storage.exists():
            return global_storage, user_dir

    if system == 'Darwin':
        mac_base = Path.home() / 'Library' / 'Application Support'
        global_storage = mac_base / GLOBAL_STORAGE_SUBPATH
        user_dir = mac_base / USER_SUBPATH
        if global_storage.exists():
            return global_storage, user_dir

    return None, None


def _get_default_backup_dir() -> Path:
    """Get default backup directory."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_base = Path.home() / ".cursor-backups"
    return backup_base / f"backup_{timestamp}"


def _test_database(db_path: Path) -> dict[str, Any]:
    """Test database health and return diagnostics."""
    result: dict[str, Any] = {
        'path': str(db_path),
        'exists': db_path.exists(),
        'size_mb': 0,
        'readable': False,
        'item_count': 0,
        'bubble_count': 0,
        'error': None,
    }
    
    if not db_path.exists():
        result['error'] = 'File does not exist'
        return result
    
    result['size_mb'] = round(db_path.stat().st_size / (1024 * 1024), 2)
    
    try:
        conn = _connect_database(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM ItemTable")
        result['item_count'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM cursorDiskKV WHERE key LIKE 'bubbleId:%'")
        result['bubble_count'] = cursor.fetchone()[0]
        
        result['readable'] = True
        conn.close()
    except sqlite3.OperationalError as e:
        result['error'] = str(e)
    except Exception as e:
        result['error'] = f"Unexpected error: {e}"
    
    return result


def _export_chat_history(db_path: Path, output_file: Path) -> int:
    """Export all chat history from cursorDiskKV to JSON."""
    conn = _connect_database(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT key, value FROM cursorDiskKV WHERE key LIKE 'bubbleId:%'")
    rows = cursor.fetchall()
    
    # Store as list of {key, value} for restoration
    data = []
    for key, value in rows:
        try:
            # Value is stored as blob, decode it
            if isinstance(value, bytes):
                value_str = value.decode('utf-8', errors='replace')
            else:
                value_str = str(value)
            data.append({'key': key, 'value': value_str})
        except Exception:
            # Skip undecodable entries
            continue
    
    conn.close()
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    return len(data)


def _export_agent_data(db_path: Path, output_file: Path) -> int:
    """Export agent KV data (agentKv:blob:*) to JSON."""
    conn = _connect_database(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT key, value FROM cursorDiskKV WHERE key LIKE 'agentKv:%'")
    rows = cursor.fetchall()
    
    data = []
    for key, value in rows:
        try:
            if isinstance(value, bytes):
                value_str = value.decode('utf-8', errors='replace')
            else:
                value_str = str(value)
            data.append({'key': key, 'value': value_str})
        except Exception:
            continue
    
    conn.close()
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    return len(data)


def _export_item_table(db_path: Path, output_file: Path) -> int:
    """Export ItemTable settings to JSON."""
    conn = _connect_database(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT key, value FROM ItemTable")
    rows = cursor.fetchall()
    
    data = {}
    for key, value in rows:
        try:
            if isinstance(value, bytes):
                value_str = value.decode('utf-8', errors='replace')
            else:
                value_str = str(value)
            data[key] = value_str
        except Exception:
            continue
    
    conn.close()
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    return len(data)


def _copy_config_files(user_dir: Path, backup_dir: Path, dry_run: bool) -> list[str]:
    """Copy configuration files to backup directory."""
    copied = []
    config_backup_dir = backup_dir / "config"
    
    if not dry_run:
        config_backup_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy individual files
    for filename in CONFIG_FILES:
        src = user_dir / filename
        if src.exists():
            dst = config_backup_dir / filename
            if not dry_run:
                shutil.copy2(src, dst)
            copied.append(filename)
    
    # Copy directories
    for dirname in CONFIG_DIRS:
        src = user_dir / dirname
        if src.exists() and src.is_dir():
            dst = config_backup_dir / dirname
            if not dry_run:
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
            copied.append(f"{dirname}/")
    
    return copied


def cmd_backup(args: argparse.Namespace) -> int:
    """Execute backup."""
    global_storage, user_dir = _get_cursor_directories()
    
    if not global_storage:
        print("Error: Cannot find Cursor globalStorage directory")
        return 1
    
    db_path = global_storage / DB_FILENAME
    diag = _test_database(db_path)
    
    if not diag['readable']:
        print(f"Error: Database not readable: {diag['error']}")
        return 1
    
    # Determine output directory
    if args.output_dir:
        backup_dir = Path(args.output_dir)
    else:
        backup_dir = _get_default_backup_dir()
    
    print(f"Cursor Data Backup")
    print("=" * 60)
    print(f"Source database: {db_path}")
    print(f"  Size: {diag['size_mb']} MB")
    print(f"  Chat messages: {diag['bubble_count']}")
    print(f"  Settings: {diag['item_count']}")
    print(f"Backup directory: {backup_dir}")
    print("")
    
    if args.dry_run:
        print("[DRY RUN] Would create backup with:")
        print(f"  - chat_history.json ({diag['bubble_count']} messages)")
        print(f"  - item_table.json ({diag['item_count']} settings)")
        print(f"  - agent_data.json")
        
        if user_dir and user_dir.exists():
            config_files = _copy_config_files(user_dir, backup_dir, dry_run=True)
            print(f"  - config/ ({', '.join(config_files)})")
        
        return 0
    
    # Create backup directory
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    # Export chat history
    print("Exporting chat history...", end=" ", flush=True)
    chat_file = backup_dir / "chat_history.json"
    chat_count = _export_chat_history(db_path, chat_file)
    print(f"Done ({chat_count} messages)")
    
    # Export agent data
    print("Exporting agent data...", end=" ", flush=True)
    agent_file = backup_dir / "agent_data.json"
    agent_count = _export_agent_data(db_path, agent_file)
    print(f"Done ({agent_count} entries)")
    
    # Export ItemTable
    print("Exporting settings...", end=" ", flush=True)
    settings_file = backup_dir / "item_table.json"
    settings_count = _export_item_table(db_path, settings_file)
    print(f"Done ({settings_count} settings)")
    
    # Copy config files
    config_files: list[str] = []
    if user_dir and user_dir.exists():
        print("Copying config files...", end=" ", flush=True)
        config_files = _copy_config_files(user_dir, backup_dir, dry_run=False)
        print(f"Done ({', '.join(config_files)})")
    
    # Create manifest
    manifest = {
        'backup_time': datetime.now().isoformat(),
        'source_db': str(db_path),
        'db_size_mb': diag['size_mb'],
        'chat_count': chat_count,
        'agent_count': agent_count,
        'settings_count': settings_count,
        'config_files': config_files,
    }
    
    manifest_file = backup_dir / "manifest.json"
    with open(manifest_file, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)
    
    print("")
    print("=" * 60)
    print(f"Backup complete: {backup_dir}")
    print(f"  Total files: {len(list(backup_dir.rglob('*')))}")
    
    return 0


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Comprehensive backup of Cursor data"
    )
    parser.add_argument(
        '--output-dir', '-o',
        help='Output directory for backup (default: ~/.cursor-backups/backup_TIMESTAMP)'
    )
    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='Show what would be backed up without actually doing it'
    )
    
    args = parser.parse_args()
    return cmd_backup(args)


if __name__ == '__main__':
    sys.exit(main())
