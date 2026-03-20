#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""
Clone prod Ogham memories into the dev memories DB for parity testing.
Copies memories, activations, and memory_links tables.
Uses INSERT OR IGNORE to avoid overwriting existing dev memories.

Usage:
    uv run --script .cursor/skills/dev-startup/scripts/clone-prod-memories.py [--dry-run]
"""

import os
import sqlite3
import sys


def clone_memories(dry_run: bool = False) -> None:
    appdata = os.environ.get("APPDATA", "")
    if not appdata:
        print("ERROR: APPDATA environment variable not set", file=sys.stderr)
        sys.exit(1)

    prod_runtime_db = os.path.join(appdata, "rootstock", "graft_runtime.db")
    dev_memories_db = os.path.join(appdata, "rootstock-dev", "graft_memories.db")

    if not os.path.exists(prod_runtime_db):
        print(f"ERROR: Prod runtime DB not found at {prod_runtime_db}", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(dev_memories_db):
        print(f"ERROR: Dev memories DB not found at {dev_memories_db}", file=sys.stderr)
        sys.exit(1)

    print(f"Source (prod runtime): {prod_runtime_db}")
    print(f"Destination (dev memories): {dev_memories_db}")

    prod = sqlite3.connect(f"file:{prod_runtime_db}?mode=ro", uri=True)
    prod.row_factory = sqlite3.Row

    dev = sqlite3.connect(dev_memories_db)

    try:
        # Count source rows
        prod_counts = {
            table: prod.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("memories", "activations", "memory_links")
        }
        # Count dest rows before
        dev_before = {
            table: dev.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            if _table_exists(dev, table)
            else 0
            for table in ("memories", "activations", "memory_links")
        }

        print(f"\nProd: memories={prod_counts['memories']} activations={prod_counts['activations']} memory_links={prod_counts['memory_links']}")
        print(f"Dev (before): memories={dev_before['memories']} activations={dev_before['activations']} memory_links={dev_before['memory_links']}")

        if dry_run:
            print("\n[dry-run] No changes made.")
            return

        with dev:
            # Copy memories
            rows = prod.execute(
                "SELECT id, memory_kind, scope_type, scope_key, claim, tags, "
                "evidence_count, activation_base, decay_d, utility_score, "
                "staleness_score, contradiction_count, retention_preference, "
                "retention_reason, status, source, session_id, project_id, "
                "valid_from, valid_to, supersedes_id FROM memories"
            ).fetchall()

            dev.executemany(
                "INSERT OR IGNORE INTO memories "
                "(id, memory_kind, scope_type, scope_key, claim, tags, "
                "evidence_count, activation_base, decay_d, utility_score, "
                "staleness_score, contradiction_count, retention_preference, "
                "retention_reason, status, source, session_id, project_id, "
                "valid_from, valid_to, supersedes_id) VALUES "
                "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                [tuple(r) for r in rows],
            )
            memories_inserted = dev.execute(
                "SELECT changes()"
            ).fetchone()[0]

            # Copy activations
            act_rows = prod.execute(
                "SELECT id, memory_id, session_id, trigger_type, trigger_scope, "
                "rank_score, shown_at, used_in_action, feedback_label, outcome_delta "
                "FROM activations"
            ).fetchall()
            dev.executemany(
                "INSERT OR IGNORE INTO activations "
                "(id, memory_id, session_id, trigger_type, trigger_scope, "
                "rank_score, shown_at, used_in_action, feedback_label, outcome_delta) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                [tuple(r) for r in act_rows],
            )
            activations_inserted = dev.execute("SELECT changes()").fetchone()[0]

            # Copy memory_links
            link_rows = prod.execute(
                "SELECT id, from_id, to_id, relationship, created_at FROM memory_links"
            ).fetchall()
            dev.executemany(
                "INSERT OR IGNORE INTO memory_links "
                "(id, from_id, to_id, relationship, created_at) VALUES (?,?,?,?,?)",
                [tuple(r) for r in link_rows],
            )
            links_inserted = dev.execute("SELECT changes()").fetchone()[0]

            # Rebuild FTS index if it exists
            if _table_exists(dev, "memory_fts"):
                dev.execute("INSERT INTO memory_fts(memory_fts) VALUES('rebuild')")
                print("\nFTS index rebuilt.")

        dev_after = {
            table: dev.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            if _table_exists(dev, table)
            else 0
            for table in ("memories", "activations", "memory_links")
        }

        print(f"\nInserted: memories={memories_inserted} activations={activations_inserted} links={links_inserted}")
        print(f"Dev (after): memories={dev_after['memories']} activations={dev_after['activations']} memory_links={dev_after['memory_links']}")
        print("\nDone.")

    finally:
        prod.close()
        dev.close()


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    result = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return result is not None


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    clone_memories(dry_run)
