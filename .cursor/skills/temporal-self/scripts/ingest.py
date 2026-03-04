#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# pyright: reportMissingImports=false
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from typing import Any

from lib.cache import (
    get_db_path,
    init_db,
    insert_causal_links,
    insert_events,
    upsert_scan_meta,
)
from lib.git_analyzer import collect_workspace_git_events
from lib.transcript_parser import parse_transcripts, summarize_transcript_event_types


def _project_slug(workspace_path: Path) -> str:
    return str(workspace_path.resolve()).replace(":", "").replace("\\", "-").replace("/", "-")


def _auto_detect_transcripts_dir(workspace_path: Path) -> Path | None:
    slug = _project_slug(workspace_path)
    candidate = Path.home() / ".cursor" / "projects" / slug / "agent-transcripts"
    if candidate.is_dir():
        return candidate

    projects_root = Path.home() / ".cursor" / "projects"
    if not projects_root.exists():
        return None

    for project_dir in projects_root.iterdir():
        transcripts_dir = project_dir / "agent-transcripts"
        if not transcripts_dir.is_dir():
            continue
        if slug.lower() in project_dir.name.lower() or project_dir.name.lower() in slug.lower():
            return transcripts_dir
    return None


def _discover_all_transcript_dirs() -> list[Path]:
    """Find transcript directories across ALL Cursor workspaces."""
    projects_root = Path.home() / ".cursor" / "projects"
    if not projects_root.exists():
        return []
    dirs: list[Path] = []
    for project_dir in projects_root.iterdir():
        if not project_dir.is_dir():
            continue
        transcripts = project_dir / "agent-transcripts"
        if transcripts.is_dir():
            dirs.append(transcripts)
    return sorted(dirs)


def _discover_transcript_files(transcripts_dirs: list[Path]) -> list[Path]:
    """Find transcript files across multiple directories."""
    files: list[Path] = []
    for transcripts_dir in transcripts_dirs:
        if not transcripts_dir.exists():
            continue
        files.extend(transcripts_dir.glob("*.txt"))
        files.extend(transcripts_dir.glob("**/*.jsonl"))
    return sorted(set(files))


def _dedupe_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for event in events:
        by_id[event["id"]] = event
    deduped = list(by_id.values())
    deduped.sort(key=lambda event: (event["event_time"], event["id"]))
    return deduped


def _fetch_count(conn: sqlite3.Connection, table_name: str) -> int:
    row = conn.execute(f"SELECT COUNT(*) AS count_value FROM {table_name}").fetchone()
    return int(row["count_value"] if row else 0)


def run_ingest(
    workspace_path: Path,
    days: int,
    transcripts_override: Path | None,
    verbose: bool,
) -> int:
    if transcripts_override:
        transcripts_dirs = [transcripts_override]
    else:
        # Gather from all Cursor workspaces for cross-project memory.
        transcripts_dirs = _discover_all_transcript_dirs()
        # Include current workspace auto-detected transcripts as fallback.
        auto_dir = _auto_detect_transcripts_dir(workspace_path)
        if auto_dir and auto_dir not in transcripts_dirs:
            transcripts_dirs.append(auto_dir)

    transcript_files = _discover_transcript_files(transcripts_dirs)
    transcript_events, causal_links, sessions = parse_transcripts(
        transcript_files,
        workspace_path,
        verbose=verbose,
    )

    git_events = collect_workspace_git_events(workspace_path, days=days, verbose=verbose)
    all_events = _dedupe_events([*transcript_events, *git_events])

    db_path = get_db_path(workspace_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        init_db(conn)
        inserted_events = insert_events(conn, all_events)
        inserted_links = insert_causal_links(conn, causal_links)

        events_total = _fetch_count(conn, "events")
        episodes_total = _fetch_count(conn, "episodes")
        memories_total = _fetch_count(conn, "memories")
        upsert_scan_meta(
            conn=conn,
            workspace_path=workspace_path,
            sessions=len(sessions),
            events=events_total,
            episodes=episodes_total,
            memories=memories_total,
        )
    finally:
        conn.close()

    print(f"workspace: {workspace_path}")
    print(f"db: {db_path}")
    print(f"transcript_dirs: {len(transcripts_dirs)}")
    print(f"transcript_files: {len(transcript_files)}")
    print(f"git_events: {len(git_events)}")
    print(f"combined_events: {len(all_events)}")
    print(f"inserted_events: {inserted_events}")
    print(f"inserted_causal_links: {inserted_links}")

    if verbose and transcripts_dirs:
        print("transcript_dirs_list:")
        for transcripts_dir in sorted(transcripts_dirs):
            print(f"- {transcripts_dir}")

    if verbose and transcript_events:
        counts = summarize_transcript_event_types(transcript_events)
        print(f"transcript_event_types: {counts}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ingest transcript and git events into temporal-self SQLite cache.",
    )
    parser.add_argument("workspace_path", type=Path)
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--transcripts", type=Path, default=None)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    workspace_path = args.workspace_path.resolve()
    if not workspace_path.exists():
        print(f"error: workspace does not exist: {workspace_path}")
        return 2

    days = max(1, int(args.days))
    transcripts_override = args.transcripts.resolve() if args.transcripts else None
    return run_ingest(
        workspace_path=workspace_path,
        days=days,
        transcripts_override=transcripts_override,
        verbose=bool(args.verbose),
    )


if __name__ == "__main__":
    raise SystemExit(main())

