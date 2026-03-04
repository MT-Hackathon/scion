#!/usr/bin/env python3
"""
Safe restore of Cursor data with orphan prevention.

This script restores chat history and settings while preventing the "orphan chat"
issue that causes Cursor UI to loop infinitely searching for non-existent chats.

Usage:
  restore-cursor-data.py BACKUP_DIR                    # Restore from backup directory
  restore-cursor-data.py BACKUP_DIR --chats-only       # Only restore chat history
  restore-cursor-data.py BACKUP_DIR --config-only      # Only restore config files
  restore-cursor-data.py BACKUP_DIR --dry-run          # Show what would be restored
  restore-cursor-data.py --from-db SOURCE.vscdb        # Restore directly from a database file
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Constants
DEFAULT_USER = 'cmb115'
DB_FILENAME = 'state.vscdb'
GLOBAL_STORAGE_SUBPATH = 'Cursor/User/globalStorage'
USER_SUBPATH = 'Cursor/User'
TIMEOUT_SECONDS = 30

# Keys that reference conversation IDs and must be reset to prevent orphans
ORPHAN_PREVENTION_KEYS = [
    'backgroundComposer.windowBcMapping',
    'chat.workspaceTransfer',
    'conversationClassificationScoredConversations',
    'composer.planRegistry',
    'composer.planRedirects',
]

# Keys to preserve during restore (auth, privacy settings)
PRESERVE_KEYS = [
    'cursorAuth/accessToken',
    'cursorAuth/refreshToken',
    'cursorAuth/cachedEmail',
    'cursorAuth/cachedSignUpType',
    'cursorAuth/stripeMembershipType',
    'cursorAuth/stripeSubscriptionStatus',
    'cursorai/donotchange/hasReconciledNewPrivacyModeWithServerOnUpgrade',
    'cursorai/donotchange/newPrivacyMode2',
    'cursorai/donotchange/newPrivacyModeHoursRemainingInGracePeriod',
    'cursorai/donotchange/partnerDataShare',
]


def _get_cursor_directories() -> tuple[Path | None, Path | None]:
    """Find Cursor globalStorage and User directories."""
    if os.path.exists('/mnt/c'):
        user = os.environ.get('USER', DEFAULT_USER)
        base = Path(f"/mnt/c/Users/{user}/AppData/Roaming")
        global_storage = base / GLOBAL_STORAGE_SUBPATH
        user_dir = base / USER_SUBPATH
        if global_storage.exists():
            return global_storage, user_dir
    
    # Linux native
    linux_base = Path.home() / ".config"
    global_storage = linux_base / GLOBAL_STORAGE_SUBPATH
    user_dir = linux_base / USER_SUBPATH
    if global_storage.exists():
        return global_storage, user_dir
    
    # macOS
    mac_base = Path.home() / "Library" / "Application Support"
    global_storage = mac_base / GLOBAL_STORAGE_SUBPATH
    user_dir = mac_base / USER_SUBPATH
    if global_storage.exists():
        return global_storage, user_dir
    
    return None, None


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
        conn = sqlite3.connect(str(db_path), timeout=TIMEOUT_SECONDS)
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


def _get_preserved_values(db_path: Path) -> dict[str, str]:
    """Get values for keys that should be preserved during restore."""
    preserved = {}
    
    try:
        conn = sqlite3.connect(str(db_path), timeout=TIMEOUT_SECONDS)
        cursor = conn.cursor()
        
        for key in PRESERVE_KEYS:
            cursor.execute("SELECT value FROM ItemTable WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                value = row[0]
                if isinstance(value, bytes):
                    value = value.decode('utf-8', errors='replace')
                preserved[key] = value
        
        conn.close()
    except Exception:
        pass
    
    return preserved


def _clean_orphan_references(db_path: Path, dry_run: bool = False) -> list[str]:
    """Clean up ItemTable keys that reference non-existent conversations."""
    cleaned = []
    
    conn = sqlite3.connect(str(db_path), timeout=TIMEOUT_SECONDS)
    cursor = conn.cursor()
    
    for key in ORPHAN_PREVENTION_KEYS:
        cursor.execute("SELECT value FROM ItemTable WHERE key = ?", (key,))
        row = cursor.fetchone()
        if row:
            if not dry_run:
                if key == 'backgroundComposer.windowBcMapping':
                    # Reset to empty mapping
                    cursor.execute(
                        "UPDATE ItemTable SET value = ? WHERE key = ?",
                        ('{}', key)
                    )
                else:
                    # Delete other orphan-prone keys
                    cursor.execute("DELETE FROM ItemTable WHERE key = ?", (key,))
            cleaned.append(key)
    
    if not dry_run:
        conn.commit()
    conn.close()
    
    return cleaned


def _restore_chat_history(source_file: Path, db_path: Path, dry_run: bool = False) -> int:
    """Restore chat history from JSON backup."""
    with open(source_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if dry_run:
        return len(data)
    
    conn = sqlite3.connect(str(db_path), timeout=TIMEOUT_SECONDS)
    cursor = conn.cursor()
    
    # Insert or replace chat entries
    for entry in data:
        key = entry['key']
        value = entry['value']
        cursor.execute(
            "INSERT OR REPLACE INTO cursorDiskKV (key, value) VALUES (?, ?)",
            (key, value.encode('utf-8') if isinstance(value, str) else value)
        )
    
    conn.commit()
    conn.close()
    
    return len(data)


def _restore_agent_data(source_file: Path, db_path: Path, dry_run: bool = False) -> int:
    """Restore agent data from JSON backup."""
    if not source_file.exists():
        return 0
    
    with open(source_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if dry_run:
        return len(data)
    
    conn = sqlite3.connect(str(db_path), timeout=TIMEOUT_SECONDS)
    cursor = conn.cursor()
    
    for entry in data:
        key = entry['key']
        value = entry['value']
        cursor.execute(
            "INSERT OR REPLACE INTO cursorDiskKV (key, value) VALUES (?, ?)",
            (key, value.encode('utf-8') if isinstance(value, str) else value)
        )
    
    conn.commit()
    conn.close()
    
    return len(data)


def _restore_from_database(source_db: Path, target_db: Path, dry_run: bool = False) -> dict[str, int]:
    """Restore chat history directly from another database file."""
    source_diag = _test_database(source_db)
    if not source_diag['readable']:
        raise ValueError(f"Source database not readable: {source_diag['error']}")
    
    if dry_run:
        return {
            'chats': source_diag['bubble_count'],
            'agents': 0,  # Can't easily count without querying
        }
    
    # Get preserved values from target before modification
    preserved = _get_preserved_values(target_db)
    
    source_conn = sqlite3.connect(str(source_db), timeout=TIMEOUT_SECONDS)
    target_conn = sqlite3.connect(str(target_db), timeout=TIMEOUT_SECONDS)
    
    source_cursor = source_conn.cursor()
    target_cursor = target_conn.cursor()
    
    # Restore chat history
    source_cursor.execute("SELECT key, value FROM cursorDiskKV WHERE key LIKE 'bubbleId:%'")
    chat_count = 0
    for key, value in source_cursor.fetchall():
        target_cursor.execute(
            "INSERT OR REPLACE INTO cursorDiskKV (key, value) VALUES (?, ?)",
            (key, value)
        )
        chat_count += 1
    
    # Restore agent data
    source_cursor.execute("SELECT key, value FROM cursorDiskKV WHERE key LIKE 'agentKv:%'")
    agent_count = 0
    for key, value in source_cursor.fetchall():
        target_cursor.execute(
            "INSERT OR REPLACE INTO cursorDiskKV (key, value) VALUES (?, ?)",
            (key, value)
        )
        agent_count += 1
    
    target_conn.commit()
    
    source_conn.close()
    target_conn.close()
    
    # Restore preserved values
    if preserved:
        conn = sqlite3.connect(str(target_db), timeout=TIMEOUT_SECONDS)
        cursor = conn.cursor()
        for key, value in preserved.items():
            cursor.execute(
                "INSERT OR REPLACE INTO ItemTable (key, value) VALUES (?, ?)",
                (key, value)
            )
        conn.commit()
        conn.close()
    
    return {'chats': chat_count, 'agents': agent_count}


def _restore_config_files(backup_dir: Path, user_dir: Path, dry_run: bool = False) -> list[str]:
    """Restore configuration files from backup."""
    config_dir = backup_dir / "config"
    if not config_dir.exists():
        return []
    
    restored = []
    
    for item in config_dir.iterdir():
        target = user_dir / item.name
        if item.is_file():
            if not dry_run:
                shutil.copy2(item, target)
            restored.append(item.name)
        elif item.is_dir():
            if not dry_run:
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(item, target)
            restored.append(f"{item.name}/")
    
    return restored


def cmd_restore(args: argparse.Namespace) -> int:
    """Execute restore."""
    global_storage, user_dir = _get_cursor_directories()
    
    if not global_storage:
        print("Error: Cannot find Cursor globalStorage directory")
        return 1
    
    db_path = global_storage / DB_FILENAME
    
    # Check if restoring from database directly
    if args.from_db:
        source_db = Path(args.from_db)
        if not source_db.exists():
            print(f"Error: Source database not found: {source_db}")
            return 1
        
        source_diag = _test_database(source_db)
        target_diag = _test_database(db_path)
        
        print("Cursor Data Restore (from database)")
        print("=" * 60)
        print(f"Source database: {source_db}")
        print(f"  Chat messages: {source_diag['bubble_count']}")
        print(f"Target database: {db_path}")
        print(f"  Current chats: {target_diag['bubble_count']}")
        print("")
        
        if args.dry_run:
            print("[DRY RUN] Would restore:")
            print(f"  - {source_diag['bubble_count']} chat messages")
            print("  - Agent data")
            print("  - Clean orphan references")
            return 0
        
        # Backup current database first
        backup_path = db_path.with_suffix('.vscdb.pre-restore')
        print(f"Creating backup: {backup_path.name}...", end=" ", flush=True)
        shutil.copy2(db_path, backup_path)
        print("Done")
        
        # Restore from database
        print("Restoring data...", end=" ", flush=True)
        counts = _restore_from_database(source_db, db_path, dry_run=False)
        print(f"Done ({counts['chats']} chats, {counts['agents']} agent entries)")
        
        # Clean orphan references
        print("Cleaning orphan references...", end=" ", flush=True)
        cleaned = _clean_orphan_references(db_path, dry_run=False)
        print(f"Done ({len(cleaned)} keys)")
        
        print("")
        print("=" * 60)
        print("Restore complete! Restart Cursor to see changes.")
        return 0
    
    # Restoring from backup directory
    backup_dir = Path(args.backup_dir)
    if not backup_dir.exists():
        print(f"Error: Backup directory not found: {backup_dir}")
        return 1
    
    # Load manifest
    manifest_file = backup_dir / "manifest.json"
    if manifest_file.exists():
        with open(manifest_file, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
    else:
        manifest = {}
    
    target_diag = _test_database(db_path)
    
    print("Cursor Data Restore")
    print("=" * 60)
    print(f"Backup directory: {backup_dir}")
    if manifest:
        print(f"  Backup time: {manifest.get('backup_time', 'unknown')}")
        print(f"  Chat count: {manifest.get('chat_count', 'unknown')}")
    print(f"Target database: {db_path}")
    print(f"  Current chats: {target_diag['bubble_count']}")
    print("")
    
    # Determine what to restore
    restore_chats = not args.config_only
    restore_config = not args.chats_only
    
    if args.dry_run:
        print("[DRY RUN] Would restore:")
        
        if restore_chats:
            chat_file = backup_dir / "chat_history.json"
            if chat_file.exists():
                count = _restore_chat_history(chat_file, db_path, dry_run=True)
                print(f"  - {count} chat messages")
            
            agent_file = backup_dir / "agent_data.json"
            if agent_file.exists():
                count = _restore_agent_data(agent_file, db_path, dry_run=True)
                print(f"  - {count} agent entries")
            
            print("  - Clean orphan references")
        
        if restore_config and user_dir:
            config_files = _restore_config_files(backup_dir, user_dir, dry_run=True)
            if config_files:
                print(f"  - Config files: {', '.join(config_files)}")
        
        return 0
    
    # Create pre-restore backup
    backup_path = db_path.with_suffix('.vscdb.pre-restore')
    print(f"Creating backup: {backup_path.name}...", end=" ", flush=True)
    shutil.copy2(db_path, backup_path)
    print("Done")
    
    if restore_chats:
        # Restore chat history
        chat_file = backup_dir / "chat_history.json"
        if chat_file.exists():
            print("Restoring chat history...", end=" ", flush=True)
            count = _restore_chat_history(chat_file, db_path, dry_run=False)
            print(f"Done ({count} messages)")
        
        # Restore agent data
        agent_file = backup_dir / "agent_data.json"
        if agent_file.exists():
            print("Restoring agent data...", end=" ", flush=True)
            count = _restore_agent_data(agent_file, db_path, dry_run=False)
            print(f"Done ({count} entries)")
        
        # Clean orphan references
        print("Cleaning orphan references...", end=" ", flush=True)
        cleaned = _clean_orphan_references(db_path, dry_run=False)
        print(f"Done ({len(cleaned)} keys)")
    
    if restore_config and user_dir:
        # Restore config files
        print("Restoring config files...", end=" ", flush=True)
        config_files = _restore_config_files(backup_dir, user_dir, dry_run=False)
        if config_files:
            print(f"Done ({', '.join(config_files)})")
        else:
            print("None found")
    
    print("")
    print("=" * 60)
    print("Restore complete! Restart Cursor to see changes.")
    
    return 0


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Safe restore of Cursor data with orphan prevention"
    )
    parser.add_argument(
        'backup_dir',
        nargs='?',
        help='Backup directory to restore from'
    )
    parser.add_argument(
        '--from-db',
        help='Restore directly from a database file (e.g., state.vscdb.corrupted.*)'
    )
    parser.add_argument(
        '--chats-only',
        action='store_true',
        help='Only restore chat history (not config files)'
    )
    parser.add_argument(
        '--config-only',
        action='store_true',
        help='Only restore config files (not chat history)'
    )
    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='Show what would be restored without actually doing it'
    )
    
    args = parser.parse_args()
    
    if not args.backup_dir and not args.from_db:
        parser.error("Either BACKUP_DIR or --from-db is required")
    
    return cmd_restore(args)


if __name__ == '__main__':
    sys.exit(main())
