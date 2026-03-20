#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Sync the AI memory corpus (ogham_db) between Rootstock instances.

The memory corpus is the AI's accumulated knowledge — decisions, learnings,
calibrations, and session continuity data. It is NOT general user application
data. Users can write into user_memories; the bulk of the corpus is AI-authored.

This script syncs graft_memories.db between instances:
  - dev  (debug binary, port 7701): %APPDATA%\\rootstock-dev\\graft_memories.db
  - prod (release binary, port 7700): %APPDATA%\\rootstock\\graft_memories.db
  - remote (new laptop or Mycelium/ogham-1 over SMB): custom --dest path

Mycelium (ogham-1) eventually handles sync via Turso. This script is the
manual bridge until that infrastructure is wired up.

Usage:
  # Preview: show what would be copied (dry run)
  uv run --script .cursor/skills/dev-startup/scripts/sync-memories.py --dry-run

  # After dev testing: promote AI memories to prod
  uv run --script .cursor/skills/dev-startup/scripts/sync-memories.py --direction dev-to-prod

  # Seed dev from prod (after a promote cycle)
  uv run --script .cursor/skills/dev-startup/scripts/sync-memories.py --direction prod-to-dev

  # Push prod corpus to a new machine over SMB (run once to seed)
  uv run --script .cursor/skills/dev-startup/scripts/sync-memories.py \\
    --direction prod-to-path \\
    --dest "\\\\LAPTOP-NAME\\Users\\cmb115\\AppData\\Roaming\\rootstock\\graft_memories.db"

Copies rows that exist in source but not in dest (by memory ID).
INSERT OR IGNORE — safe to run repeatedly; never overwrites existing rows.

Simpler alternative during testing: point dev binary at prod ogham_db directly:
  $env:GRAFT_MEMORIES_DB_PATH = "$env:APPDATA\\rootstock\\graft_memories.db"
  .\\target\\debug\\rootstock.exe --mcp
"""
from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

def _appdata() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata)
    # Linux/macOS fallback
    return Path.home() / ".local" / "share"


def dev_db_path() -> Path:
    return _appdata() / "rootstock-dev" / "graft_memories.db"


def prod_db_path() -> Path:
    return _appdata() / "rootstock" / "graft_memories.db"


# ---------------------------------------------------------------------------
# Core sync logic
# ---------------------------------------------------------------------------

MEMORY_TABLES = [
    "memories",
    "memory_vectors",
    "memory_links",
    "memory_events",
    "memory_knowledge_links",
    "user_memories",
    "user_memory_vectors",
]

# Tables that reference memories.id — must be copied after memories row exists
DEPENDENT_TABLES = {
    "memory_vectors": ("memory_id", "memories", "id"),
    "memory_links": ("from_id", "memories", "id"),
    "memory_events": ("memory_id", "memories", "id"),
    "memory_knowledge_links": ("memory_id", "memories", "id"),
    "user_memories": None,          # standalone
    "user_memory_vectors": ("memory_id", "user_memories", "id"),
}


def get_table_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    return {r[0] for r in rows}


def count_rows(conn: sqlite3.Connection, table: str) -> int:
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]  # noqa: S608


def copy_new_memories(
    src: sqlite3.Connection,
    dst: sqlite3.Connection,
    dry_run: bool = False,
) -> dict[str, int]:
    """Copy memories rows from src that don't exist in dst (by id)."""
    src_tables = get_table_names(src)
    dst_tables = get_table_names(dst)

    stats: dict[str, int] = {}

    # --- Step 1: Copy top-level memories rows ---
    if "memories" not in src_tables:
        print("Source has no memories table — nothing to copy.", file=sys.stderr)
        return stats

    src_ids = {r[0] for r in src.execute("SELECT id FROM memories").fetchall()}
    dst_ids = {r[0] for r in dst.execute("SELECT id FROM memories").fetchall()} \
        if "memories" in dst_tables else set()

    new_ids = src_ids - dst_ids
    if not new_ids:
        print("No new memories to copy.")
        return stats

    print(f"Found {len(new_ids)} new memories to copy.")

    if not dry_run:
        placeholders = ",".join("?" for _ in new_ids)
        rows = src.execute(
            f"SELECT * FROM memories WHERE id IN ({placeholders})",  # noqa: S608
            list(new_ids),
        ).fetchall()
        cols = [d[0] for d in src.execute("SELECT * FROM memories LIMIT 0").description]
        dst.executemany(
            f"INSERT OR IGNORE INTO memories ({','.join(cols)}) "  # noqa: S608
            f"VALUES ({','.join('?' for _ in cols)})",
            rows,
        )
        dst.commit()
        stats["memories"] = len(rows)
        print(f"  Copied {len(rows)} memory rows.")
    else:
        stats["memories"] = len(new_ids)
        print(f"  [dry-run] Would copy {len(new_ids)} memories.")

    # --- Step 2: Copy dependent rows for the new memories ---
    for table, dep in DEPENDENT_TABLES.items():
        if table == "memories" or table not in src_tables:
            continue
        if "user_memories" in table:
            # Copy all user_memories not already in dst
            _copy_table_by_column(src, dst, table, "id", dry_run, stats)
            continue
        if dep is None:
            continue

        fk_col, _ref_table, _ref_col = dep
        placeholders = ",".join("?" for _ in new_ids)
        try:
            dep_rows = src.execute(
                f"SELECT * FROM {table} WHERE {fk_col} IN ({placeholders})",  # noqa: S608
                list(new_ids),
            ).fetchall()
        except sqlite3.OperationalError:
            continue  # table or column may not exist in older schema

        if not dep_rows:
            continue

        cols = [d[0] for d in src.execute(
            f"SELECT * FROM {table} LIMIT 0"  # noqa: S608
        ).description]

        if not dry_run:
            dst.executemany(
                f"INSERT OR IGNORE INTO {table} ({','.join(cols)}) "  # noqa: S608
                f"VALUES ({','.join('?' for _ in cols)})",
                dep_rows,
            )
            dst.commit()
            stats[table] = len(dep_rows)
            print(f"  Copied {len(dep_rows)} rows → {table}.")
        else:
            stats[table] = len(dep_rows)
            print(f"  [dry-run] Would copy {len(dep_rows)} rows → {table}.")

    return stats


def _copy_table_by_column(
    src: sqlite3.Connection,
    dst: sqlite3.Connection,
    table: str,
    id_col: str,
    dry_run: bool,
    stats: dict[str, int],
) -> None:
    src_tables = get_table_names(src)
    dst_tables = get_table_names(dst)
    if table not in src_tables:
        return
    src_ids = {r[0] for r in src.execute(
        f"SELECT {id_col} FROM {table}"  # noqa: S608
    ).fetchall()}
    dst_ids = {r[0] for r in dst.execute(
        f"SELECT {id_col} FROM {table}"  # noqa: S608
    ).fetchall()} if table in dst_tables else set()
    new_ids = src_ids - dst_ids
    if not new_ids:
        return
    placeholders = ",".join("?" for _ in new_ids)
    rows = src.execute(
        f"SELECT * FROM {table} WHERE {id_col} IN ({placeholders})",  # noqa: S608
        list(new_ids),
    ).fetchall()
    cols = [d[0] for d in src.execute(
        f"SELECT * FROM {table} LIMIT 0"  # noqa: S608
    ).description]
    if not dry_run:
        dst.executemany(
            f"INSERT OR IGNORE INTO {table} ({','.join(cols)}) "  # noqa: S608
            f"VALUES ({','.join('?' for _ in cols)})",
            rows,
        )
        dst.commit()
        stats[table] = len(rows)
        print(f"  Copied {len(rows)} rows → {table}.")
    else:
        stats[table] = len(rows)
        print(f"  [dry-run] Would copy {len(rows)} rows → {table}.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def open_db(path: Path) -> sqlite3.Connection:
    if not path.exists():
        print(f"Database not found: {path}", file=sys.stderr)
        sys.exit(1)
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=OFF")  # avoid FK constraint errors during insert
    return conn


def print_summary(label: str, path: Path, conn: sqlite3.Connection) -> None:
    tables = get_table_names(conn)
    mem_count = count_rows(conn, "memories") if "memories" in tables else 0
    vec_count = count_rows(conn, "memory_vectors") if "memory_vectors" in tables else 0
    print(f"  {label}: {path}")
    print(f"    memories: {mem_count}  |  vectors: {vec_count}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync Rootstock memories between dev and prod databases.",
    )
    parser.add_argument(
        "--direction",
        choices=["dev-to-prod", "prod-to-dev", "prod-to-path"],
        default="dev-to-prod",
        help="Direction to copy memories (default: dev-to-prod)",
    )
    parser.add_argument(
        "--dest",
        help="Destination DB path (used with --direction prod-to-path)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be copied without writing anything",
    )
    parser.add_argument(
        "--src",
        help="Override source DB path",
    )
    args = parser.parse_args()

    dev_path = dev_db_path()
    prod_path = prod_db_path()

    print("Rootstock memory sync")
    print("=" * 50)

    if args.direction == "dev-to-prod":
        src_path = Path(args.src) if args.src else dev_path
        dst_path = prod_path
    elif args.direction == "prod-to-dev":
        src_path = Path(args.src) if args.src else prod_path
        dst_path = dev_path
    elif args.direction == "prod-to-path":
        if not args.dest:
            print("--dest required with --direction prod-to-path", file=sys.stderr)
            return 1
        src_path = Path(args.src) if args.src else prod_path
        dst_path = Path(args.dest)
        if not dst_path.exists():
            print(f"Destination not found: {dst_path}", file=sys.stderr)
            print("Tip: ensure the target machine's Rootstock has been launched at least once.", file=sys.stderr)
            return 1
    else:
        return 1

    src_conn = open_db(src_path)
    dst_conn = open_db(dst_path)

    print(f"\nSource  →  Destination {'[DRY RUN]' if args.dry_run else ''}")
    print_summary("src", src_path, src_conn)
    print_summary("dst", dst_path, dst_conn)
    print()

    stats = copy_new_memories(src_conn, dst_conn, dry_run=args.dry_run)

    print()
    if args.dry_run:
        print("Dry run complete. Run without --dry-run to apply.")
    else:
        total = sum(stats.values())
        print(f"Done. {total} total rows copied across {len(stats)} tables.")
        print("Memories copied:", stats.get("memories", 0))

    return 0


if __name__ == "__main__":
    sys.exit(main())
