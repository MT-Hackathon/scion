#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = ["ruptures>=1.1"]
# ///
# pyright: reportMissingImports=false
from __future__ import annotations

import argparse
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import ruptures as rpt

from lib.cache import clear_derived, get_db_path, init_db, insert_episodes, upsert_scan_meta
from lib.episode_classifier import classify_character, compute_features


def _fetch_events(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
SELECT id, event_time, session_id, event_type, action, artifact_key, status
FROM events
ORDER BY event_time ASC, id ASC
"""
    ).fetchall()
    return [dict(row) for row in rows]


def _build_signal(events: list[dict[str, Any]], event_type_index: dict[str, int]) -> np.ndarray:
    vectors: list[list[float]] = []
    for event in events:
        event_type = str(event.get("event_type", "unknown"))
        status = str(event.get("status", "unknown")).lower()
        status_score = 0.0
        if status == "success":
            status_score = 1.0
        elif status == "failure":
            status_score = -1.0

        vectors.append(
            [
                float(event_type_index.setdefault(event_type, len(event_type_index) + 1)),
                status_score,
                1.0 if event.get("artifact_key") else 0.0,
                1.0 if event_type in {"correction", "error_signature"} else 0.0,
            ]
        )
    return np.array(vectors, dtype=float)


def _segment_boundaries(signal: np.ndarray, min_events: int) -> list[int]:
    n = signal.shape[0]
    if n < min_events:
        return [n]

    min_size = max(2, min_events // 2)
    penalty = max(2.0, n / 5.0)
    try:
        boundaries = rpt.Pelt(model="l2", min_size=min_size, jump=3).fit(signal).predict(pen=penalty)
    except Exception:
        boundaries = [n]

    clean_boundaries = sorted({max(1, min(n, int(boundary))) for boundary in boundaries})
    if not clean_boundaries or clean_boundaries[-1] != n:
        clean_boundaries.append(n)
    return clean_boundaries


def _arc_type_for_character(character: str) -> str:
    mapping = {
        "exploratory": "exploration",
        "corrective": "repair",
        "deepening": "analysis",
        "integrative": "synthesis",
        "reductive": "compression",
        "forced": "constraint",
    }
    return mapping.get(character, "exploration")


def _build_episode_record(
    session_key: str,
    segment_index: int,
    segment_events: list[dict[str, Any]],
    change_point_score: float,
) -> dict[str, Any]:
    features = compute_features(segment_events)
    character = classify_character(features)
    start_event = segment_events[0]
    end_event = segment_events[-1]
    episode_id = f"ep:{session_key}:{segment_index}"

    event_type_counts: dict[str, int] = defaultdict(int)
    for event in segment_events:
        event_type_counts[str(event.get("event_type", "unknown"))] += 1

    conformance_score = max(0.0, min(1.0, 1.0 - (features.correction_ratio + features.error_ratio)))

    return {
        "id": episode_id,
        "strand_id": "main",
        "parent_episode_id": None,
        "fork_from_episode_id": None,
        "merge_into_episode_id": None,
        "start_event_id": start_event["id"],
        "end_event_id": end_event["id"],
        "start_time": str(start_event["event_time"]),
        "end_time": str(end_event["event_time"]),
        "dominant_character": character,
        "arc_type": _arc_type_for_character(character),
        "causal_spine_json": {
            "dominant_event_type": features.dominant_event_type,
            "dominant_action": features.dominant_action,
            "event_type_counts": dict(event_type_counts),
        },
        "decision_frame_id": None,
        "scope_key": features.dominant_scope_key,
        "change_point_score": change_point_score,
        "conformance_score": conformance_score,
        "consolidated_insight": f"{character} episode with {features.total_events} events",
        "utility_score": 0.0,
        "retention_preference": 0.0,
    }


def run_segment(workspace_path: Path, min_events: int, verbose: bool) -> int:
    db_path = get_db_path(workspace_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        init_db(conn)
        events = _fetch_events(conn)
        if not events:
            print("no events found; nothing to segment")
            return 0

        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for event in events:
            session_key = str(event["session_id"]) if event["session_id"] else "__no_session__"
            grouped[session_key].append(event)

        event_type_index: dict[str, int] = {}
        episodes: list[dict[str, Any]] = []
        for session_key, session_events in grouped.items():
            if session_key == "__no_session__":
                boundaries = [len(session_events)]
            else:
                signal = _build_signal(session_events, event_type_index)
                boundaries = _segment_boundaries(signal, min_events=min_events)
            if verbose:
                print(
                    f"[segment] session={session_key} events={len(session_events)} "
                    f"segments={len(boundaries)}"
                )
            start_idx = 0
            total_segments = len(boundaries)
            for segment_index, end_idx in enumerate(boundaries):
                segment_events = session_events[start_idx:end_idx]
                if not segment_events:
                    start_idx = end_idx
                    continue
                change_point_score = float(max(0, total_segments - 1))
                episode = _build_episode_record(
                    session_key=session_key,
                    segment_index=segment_index,
                    segment_events=segment_events,
                    change_point_score=change_point_score,
                )
                episodes.append(episode)
                start_idx = end_idx

        clear_derived(conn)
        changed_rows = insert_episodes(conn, episodes)

        events_total = conn.execute("SELECT COUNT(*) AS c FROM events").fetchone()["c"]
        episodes_total = conn.execute("SELECT COUNT(*) AS c FROM episodes").fetchone()["c"]
        memories_total = conn.execute("SELECT COUNT(*) AS c FROM memories").fetchone()["c"]
        sessions = conn.execute("SELECT COUNT(DISTINCT session_id) AS c FROM events").fetchone()["c"]
        upsert_scan_meta(
            conn=conn,
            workspace_path=workspace_path,
            sessions=int(sessions),
            events=int(events_total),
            episodes=int(episodes_total),
            memories=int(memories_total),
        )
    finally:
        conn.close()

    print(f"workspace: {workspace_path}")
    print(f"episodes_built: {len(episodes)}")
    print(f"episodes_written_changes: {changed_rows}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Segment temporal-self events into episodes.")
    parser.add_argument("workspace_path", type=Path)
    parser.add_argument("--min-events", type=int, default=5)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    workspace_path = args.workspace_path.resolve()
    if not workspace_path.exists():
        print(f"error: workspace does not exist: {workspace_path}")
        return 2

    return run_segment(
        workspace_path=workspace_path,
        min_events=max(2, int(args.min_events)),
        verbose=bool(args.verbose),
    )


if __name__ == "__main__":
    raise SystemExit(main())

