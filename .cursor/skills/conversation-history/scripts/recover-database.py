#!/usr/bin/env python3
"""
Diagnose and recover from Cursor database issues.

Usage:
  recover-database.py diagnose          # Check database health
  recover-database.py list-sources      # Find recoverable database files
  recover-database.py restore-commands  # Print restoration commands
  recover-database.py clean-orphans     # Fix orphan chat references (UI loops)
  recover-database.py clean-orphans --dry-run  # Show what would be cleaned
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Constants
DEFAULT_USER = 'cmb115'
DB_FILENAME = 'state.vscdb'
GLOBAL_STORAGE_SUBPATH = 'Cursor/User/globalStorage'
BUBBLE_KEY_PREFIX = 'bubbleId:%'
TIMEOUT_SECONDS = 10

# Keys that reference conversation IDs and can cause orphan issues
# These are reset/cleaned to prevent UI infinite loops when the referenced
# conversation no longer exists in the database
ORPHAN_PREVENTION_KEYS = [
    'backgroundComposer.windowBcMapping',
    'chat.workspaceTransfer',
    'conversationClassificationScoredConversations',
    'composer.planRegistry',
    'composer.planRedirects',
]


def _get_db_directory() -> Path | None:
    """Find the Cursor globalStorage directory."""
    if os.path.exists('/mnt/c'):
        user = os.environ.get('USER', DEFAULT_USER)
        wsl_path = Path(f"/mnt/c/Users/{user}/AppData/Roaming") / GLOBAL_STORAGE_SUBPATH
        if wsl_path.exists():
            return wsl_path
    linux_path = Path.home() / ".config" / GLOBAL_STORAGE_SUBPATH
    if linux_path.exists():
        return linux_path
    mac_path = Path.home() / "Library" / "Application Support" / GLOBAL_STORAGE_SUBPATH
    if mac_path.exists():
        return mac_path
    return None


def _test_database(db_path: Path) -> dict[str, Any]:
    """Test database health and return diagnostics."""
    result: dict[str, Any] = {
        'path': str(db_path), 'exists': db_path.exists(), 'size_mb': 0,
        'readable': False, 'item_count': 0, 'bubble_count': 0, 'error': None,
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
        cursor.execute("SELECT COUNT(*) FROM cursorDiskKV WHERE key LIKE ?", (BUBBLE_KEY_PREFIX,))
        result['bubble_count'] = cursor.fetchone()[0]
        result['readable'] = True
        conn.close()
    except sqlite3.OperationalError as e:
        result['error'] = str(e)
    except Exception as e:
        result['error'] = f"Unexpected error: {e}"
    return result


def cmd_diagnose(_args: argparse.Namespace) -> int:
    """Diagnose current database health."""
    db_dir = _get_db_directory()
    if not db_dir:
        print("Error: Cannot find Cursor globalStorage directory")
        return 1
    print(f"Database directory: {db_dir}\n")
    db_files = list(db_dir.glob(f"{DB_FILENAME}*"))
    db_files = [f for f in db_files if f.suffix not in ['.wal', '.shm', '.json']]
    if not db_files:
        print("No database files found")
        return 1
    print(f"Found {len(db_files)} database file(s):\n")
    for db_file in sorted(db_files):
        diag = _test_database(db_file)
        status = "OK" if diag['readable'] else "ERROR"
        print(f"  {db_file.name}")
        print(f"    Status: {status}")
        print(f"    Size: {diag['size_mb']} MB")
        if diag['readable']:
            print(f"    Settings: {diag['item_count']}")
            print(f"    Conversations: {diag['bubble_count']}")
        else:
            print(f"    Error: {diag['error']}")
        print("")
    print("=" * 60)
    print("RECOMMENDATIONS:")
    main_db = db_dir / DB_FILENAME
    main_diag = _test_database(main_db)
    if not main_diag['readable']:
        print("  - Main database has errors")
        print("  - Look for .corrupted.* files that may be intact")
        print("  - Run: recover-database.py list-sources")
    else:
        print("  - Main database appears healthy")
        print(f"  - Contains {main_diag['bubble_count']} conversation messages")
    return 0


def cmd_list_sources(_args: argparse.Namespace) -> int:
    """List all recoverable database sources."""
    db_dir = _get_db_directory()
    if not db_dir:
        print("Error: Cannot find Cursor globalStorage directory")
        return 1
    print("Scanning for recoverable database sources...\n")
    db_files = list(db_dir.glob(f"{DB_FILENAME}*"))
    db_files = [f for f in db_files if f.suffix not in ['.wal', '.shm', '.json']]
    recoverable: list[tuple[Path, dict[str, Any]]] = []
    for db_file in sorted(db_files, key=lambda x: x.stat().st_size, reverse=True):
        diag = _test_database(db_file)
        if diag['readable'] and diag['bubble_count'] > 0:
            recoverable.append((db_file, diag))
    if not recoverable:
        print("No recoverable sources found with conversation data")
        return 1
    print(f"Found {len(recoverable)} recoverable source(s):\n")
    for db_file, diag in recoverable:
        print(f"  Source: {db_file.name}")
        print(f"    Size: {diag['size_mb']} MB")
        print(f"    Conversations: {diag['bubble_count']}")
        print(f"    Settings: {diag['item_count']}\n")
    best = max(recoverable, key=lambda x: x[1]['bubble_count'])
    print("=" * 60)
    print("BEST RECOVERY SOURCE:")
    print(f"  {best[0].name} ({best[1]['bubble_count']} conversations)\n")
    print("To export from this source:")
    print(f'  CURSOR_DB_PATH="{best[0]}" python3 export-project-knowledge.py PROJECT json')
    return 0


def cmd_restore_commands(_args: argparse.Namespace) -> int:
    """Print commands to restore database."""
    db_dir = _get_db_directory()
    if not db_dir:
        print("Error: Cannot find Cursor globalStorage directory")
        return 1
    db_files = list(db_dir.glob(f"{DB_FILENAME}*"))
    db_files = [f for f in db_files if f.suffix not in ['.wal', '.shm', '.json']]
    best_source: Path | None = None
    best_count = 0
    for db_file in db_files:
        if db_file.name == DB_FILENAME:
            continue
        diag = _test_database(db_file)
        if diag['readable'] and diag['bubble_count'] > best_count:
            best_source = db_file
            best_count = diag['bubble_count']
    if not best_source:
        print("No recoverable source found")
        return 1
    print("=" * 60)
    print("DATABASE RESTORATION COMMANDS")
    print("=" * 60)
    print("\nIMPORTANT: Close Cursor completely before running these commands!\n")
    print("# 1. Navigate to database directory")
    print(f'cd "{db_dir}"\n')
    print("# 2. Backup current broken files")
    print(f"mv {DB_FILENAME} {DB_FILENAME}.broken")
    print(f"mv {DB_FILENAME}-wal {DB_FILENAME}-wal.broken 2>/dev/null")
    print(f"mv {DB_FILENAME}-shm {DB_FILENAME}-shm.broken 2>/dev/null\n")
    print("# 3. Restore from best source")
    print(f"cp {best_source.name} {DB_FILENAME}\n")
    print("# 4. Clean orphan references (IMPORTANT!)")
    print("python3 recover-database.py clean-orphans\n")
    print("# 5. Restart Cursor\n")
    print(f"Source: {best_source.name} ({best_count} conversations)")
    return 0


def _get_conversation_ids(db_path: Path) -> set[str]:
    """Get all conversation IDs from the database."""
    conn = sqlite3.connect(str(db_path), timeout=TIMEOUT_SECONDS)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT substr(key, 10, 36) FROM cursorDiskKV WHERE key LIKE 'bubbleId:%'")
    ids = {row[0] for row in cursor.fetchall()}
    conn.close()
    return ids


def _find_orphan_references(db_path: Path) -> dict[str, list[str]]:
    """Find ItemTable keys that reference non-existent conversations."""
    conv_ids = _get_conversation_ids(db_path)
    orphans: dict[str, list[str]] = {}
    
    conn = sqlite3.connect(str(db_path), timeout=TIMEOUT_SECONDS)
    cursor = conn.cursor()
    
    for key in ORPHAN_PREVENTION_KEYS:
        cursor.execute("SELECT value FROM ItemTable WHERE key = ?", (key,))
        row = cursor.fetchone()
        if not row:
            continue
        
        value = row[0]
        if isinstance(value, bytes):
            value = value.decode('utf-8', errors='replace')
        
        # Try to parse as JSON and find conversation ID references
        try:
            data = json.loads(value)
            # Look for UUIDs that might be conversation IDs
            value_str = json.dumps(data)
            # Extract potential UUIDs (36 char format)
            import re
            uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
            found_ids = set(re.findall(uuid_pattern, value_str, re.IGNORECASE))
            
            # Check which are orphans (not in current conversations)
            orphan_ids = found_ids - conv_ids
            if orphan_ids:
                orphans[key] = list(orphan_ids)
        except (json.JSONDecodeError, TypeError):
            # If can't parse, mark as potentially problematic
            if value and value != '{}' and value != '[]':
                orphans[key] = ['(unparseable value)']
    
    conn.close()
    return orphans


def _clean_orphan_keys(db_path: Path, dry_run: bool = False) -> dict[str, str]:
    """Clean orphan-prone keys and return what was cleaned."""
    cleaned: dict[str, str] = {}
    
    conn = sqlite3.connect(str(db_path), timeout=TIMEOUT_SECONDS)
    cursor = conn.cursor()
    
    for key in ORPHAN_PREVENTION_KEYS:
        cursor.execute("SELECT value FROM ItemTable WHERE key = ?", (key,))
        row = cursor.fetchone()
        if not row:
            continue
        
        old_value = row[0]
        if isinstance(old_value, bytes):
            old_value = old_value.decode('utf-8', errors='replace')
        
        # Determine the reset action
        if key == 'backgroundComposer.windowBcMapping':
            new_value = '{}'
            action = 'reset to empty object'
        else:
            new_value = None
            action = 'deleted'
        
        cleaned[key] = action
        
        if not dry_run:
            if new_value is not None:
                cursor.execute(
                    "UPDATE ItemTable SET value = ? WHERE key = ?",
                    (new_value, key)
                )
            else:
                cursor.execute("DELETE FROM ItemTable WHERE key = ?", (key,))
    
    if not dry_run:
        conn.commit()
    conn.close()
    
    return cleaned


def cmd_clean_orphans(args: argparse.Namespace) -> int:
    """Clean orphan chat references that cause UI loops."""
    db_dir = _get_db_directory()
    if not db_dir:
        print("Error: Cannot find Cursor globalStorage directory")
        return 1
    
    db_path = db_dir / DB_FILENAME
    diag = _test_database(db_path)
    
    if not diag['readable']:
        print(f"Error: Database not readable: {diag['error']}")
        return 1
    
    print("Orphan Reference Cleanup")
    print("=" * 60)
    print(f"Database: {db_path}")
    print(f"  Conversations: {diag['bubble_count']}")
    print("")
    
    # Find orphan references
    orphans = _find_orphan_references(db_path)
    
    if orphans:
        print("Orphan references found:")
        for key, ids in orphans.items():
            if ids[0] == '(unparseable value)':
                print(f"  {key}: contains unparseable data")
            else:
                print(f"  {key}: {len(ids)} orphan ID(s)")
        print("")
    else:
        print("No orphan references detected in parsed values.")
        print("Will clean orphan-prone keys anyway for safety.\n")
    
    if args.dry_run:
        print("[DRY RUN] Would clean these keys:")
        cleaned = _clean_orphan_keys(db_path, dry_run=True)
        for key, action in cleaned.items():
            print(f"  {key}: {action}")
        return 0
    
    # Perform cleanup
    print("Cleaning orphan-prone keys...")
    cleaned = _clean_orphan_keys(db_path, dry_run=False)
    
    for key, action in cleaned.items():
        print(f"  {key}: {action}")
    
    if not cleaned:
        print("  No keys to clean")
    
    print("")
    print("=" * 60)
    print("Cleanup complete! Restart Cursor to apply changes.")
    print("")
    print("If you still experience issues after restart:")
    print("  1. Close Cursor completely")
    print("  2. Delete state.vscdb-wal and state.vscdb-shm files")
    print("  3. Restart Cursor")
    
    return 0


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Diagnose and recover from Cursor database issues")
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    subparsers.add_parser('diagnose', help='Check database health')
    subparsers.add_parser('list-sources', help='Find recoverable database files')
    subparsers.add_parser('restore-commands', help='Print restoration commands')
    
    clean_parser = subparsers.add_parser('clean-orphans', help='Fix orphan chat references')
    clean_parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='Show what would be cleaned without making changes'
    )
    
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 0
    commands = {
        'diagnose': cmd_diagnose,
        'list-sources': cmd_list_sources,
        'restore-commands': cmd_restore_commands,
        'clean-orphans': cmd_clean_orphans,
    }
    return commands[args.command](args)


if __name__ == '__main__':
    sys.exit(main())
