#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# pyright: reportMissingImports=false
from __future__ import annotations

import argparse
import sqlite3
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Any

from lib.cache import get_db_path, init_db, insert_motifs, upsert_scan_meta


TOOLING_PREFIXES = (
    ".cursor/",
    "cursor/",
    ".claude/",
    "claude/",
    ".aiassistant/",
    "aiassistant/",
    "node_modules/",
    "target/",
    "build/",
    "dist/",
    ".git/",
    ".vscode/",
)


def _is_tooling_path(path: str | None) -> bool:
    if not path:
        return True
    normalized = path.replace("\\", "/").lstrip("./").lower()
    return any(normalized.startswith(prefix.lower().lstrip("./")) for prefix in TOOLING_PREFIXES)


def _strip_line_suffix(path: str) -> str:
    if ":" not in path:
        return path
    base, suffix = path.rsplit(":", 1)
    if suffix.replace("-", "").isdigit():
        return base
    return path


def _scope_key(path: str | None) -> str | None:
    if not path:
        return None
    if _is_tooling_path(path):
        return None
    cleaned = _strip_line_suffix(path)
    pure = PurePosixPath(cleaned)
    if pure.suffix:
        parent = pure.parent.as_posix()
        if parent and parent != ".":
            return parent
    return cleaned


def _fetch_events(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
SELECT id, event_time, event_type, action, artifact_key, status
FROM events
ORDER BY event_time ASC, id ASC
"""
    ).fetchall()
    return [dict(row) for row in rows]


def _fetch_episodes(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
SELECT id, start_time, end_time, dominant_character, scope_key, conformance_score
FROM episodes
ORDER BY start_time ASC, id ASC
"""
    ).fetchall()
    return [dict(row) for row in rows]


def _detect_corrective_loops(episodes: list[dict[str, Any]], min_support: int) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for episode in episodes:
        scope = episode.get("scope_key")
        if not scope or _is_tooling_path(str(scope)):
            continue
        grouped[str(scope)].append(episode)

    motifs: list[dict[str, Any]] = []
    for scope_key, scoped_episodes in grouped.items():
        corrective_ids = [
            episode["id"]
            for episode in scoped_episodes
            if str(episode.get("dominant_character")) in {"corrective", "forced"}
        ]
        support = len(corrective_ids)
        if support < min_support:
            continue
        first_seen = str(scoped_episodes[0]["start_time"])
        last_seen = str(scoped_episodes[-1]["end_time"] or scoped_episodes[-1]["start_time"])
        motifs.append(
            {
                "id": f"motif:corrective_loop:{scope_key}",
                "motif_type": "corrective_loop",
                "scope_type": "artifact",
                "scope_key": scope_key,
                "pattern_signature_json": {
                    "scope_key": scope_key,
                    "character": "corrective_or_forced",
                },
                "algorithm": "heuristic-v1",
                "support_count": support,
                "confidence": min(0.95, 0.4 + (support * 0.08)),
                "predictive_lift": round(support / max(1, len(scoped_episodes)), 4),
                "first_seen": first_seen,
                "last_seen": last_seen,
                "evidence_json": {"episode_ids": corrective_ids[:20]},
            }
        )
    return motifs


def _discover_cascades(events: list[dict[str, Any]], min_support: int) -> list[dict[str, Any]]:
    transitions: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for previous, current in zip(events, events[1:], strict=False):
        src_scope = _scope_key(previous.get("artifact_key"))
        dst_scope = _scope_key(current.get("artifact_key"))
        if not src_scope or not dst_scope:
            continue
        if src_scope == dst_scope:
            continue
        transitions[(src_scope, dst_scope)].append(
            {
                "event_time": current["event_time"],
                "event_id": current["id"],
                "source_event_id": previous["id"],
            }
        )

    motifs: list[dict[str, Any]] = []
    if not transitions:
        return motifs

    max_support = max(len(samples) for samples in transitions.values())
    for (src_scope, dst_scope), samples in transitions.items():
        support = len(samples)
        if support < min_support:
            continue
        scope_key = f"{src_scope}->{dst_scope}"
        motifs.append(
            {
                "id": f"motif:cascade_discovery:{scope_key}",
                "motif_type": "cascade_discovery",
                "scope_type": "transition",
                "scope_key": scope_key,
                "pattern_signature_json": {"from": src_scope, "to": dst_scope},
                "algorithm": "heuristic-v1",
                "support_count": support,
                "confidence": min(0.99, 0.2 + (support / max(1, max_support))),
                "predictive_lift": round(support / max(1, max_support), 4),
                "first_seen": str(samples[0]["event_time"]),
                "last_seen": str(samples[-1]["event_time"]),
                "evidence_json": {
                    "event_ids": [sample["event_id"] for sample in samples[:20]],
                    "source_event_ids": [sample["source_event_id"] for sample in samples[:20]],
                },
            }
        )
    return motifs


def _predict_rework(events: list[dict[str, Any]], min_support: int) -> list[dict[str, Any]]:
    scoped_events: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        scope = _scope_key(event.get("artifact_key"))
        if not scope:
            continue
        scoped_events[scope].append(event)

    motifs: list[dict[str, Any]] = []
    for scope, scope_events in scoped_events.items():
        total = len(scope_events)
        if total < min_support:
            continue
        corrective_count = 0
        error_count = 0
        for event in scope_events:
            event_type = str(event.get("event_type"))
            if event_type == "correction":
                corrective_count += 1
            if event_type == "error_signature" or str(event.get("status")) == "failure":
                error_count += 1
        risk = (corrective_count + error_count) / total
        if risk < 0.12:
            continue
        motifs.append(
            {
                "id": f"motif:rework_prediction:{scope}",
                "motif_type": "rework_prediction",
                "scope_type": "artifact",
                "scope_key": scope,
                "pattern_signature_json": {
                    "scope": scope,
                    "events": total,
                    "corrections": corrective_count,
                    "errors": error_count,
                },
                "algorithm": "heuristic-v1",
                "support_count": total,
                "confidence": min(0.99, 0.3 + risk),
                "predictive_lift": round(risk, 4),
                "first_seen": str(scope_events[0]["event_time"]),
                "last_seen": str(scope_events[-1]["event_time"]),
                "evidence_json": {
                    "event_ids": [event["id"] for event in scope_events[:30]],
                    "risk": round(risk, 4),
                },
            }
        )
    return motifs


def _detect_flow_states(episodes: list[dict[str, Any]], min_support: int) -> list[dict[str, Any]]:
    """Detect sessions/scopes with sustained integrative or deepening character."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for episode in episodes:
        scope = episode.get("scope_key")
        if not scope or _is_tooling_path(str(scope)):
            continue
        grouped[str(scope)].append(episode)

    motifs: list[dict[str, Any]] = []
    for scope_key, scoped_episodes in grouped.items():
        flow_ids = [
            episode["id"]
            for episode in scoped_episodes
            if str(episode.get("dominant_character")) in {"integrative", "deepening"}
            and float(episode.get("conformance_score", 0) or 0) >= 0.7
        ]
        support = len(flow_ids)
        if support < min_support:
            continue
        first_seen = str(scoped_episodes[0]["start_time"])
        last_seen = str(scoped_episodes[-1]["end_time"] or scoped_episodes[-1]["start_time"])
        motifs.append(
            {
                "id": f"motif:flow_state:{scope_key}",
                "motif_type": "flow_state",
                "scope_type": "artifact",
                "scope_key": scope_key,
                "pattern_signature_json": {
                    "scope_key": scope_key,
                    "character": "integrative_or_deepening",
                    "min_conformance": 0.7,
                },
                "algorithm": "heuristic-v1",
                "support_count": support,
                "confidence": min(0.95, 0.4 + (support * 0.1)),
                "predictive_lift": round(support / max(1, len(scoped_episodes)), 4),
                "first_seen": first_seen,
                "last_seen": last_seen,
                "evidence_json": {"episode_ids": flow_ids[:20]},
            }
        )
    return motifs


def _detect_effective_delegations(events: list[dict[str, Any]], min_support: int) -> list[dict[str, Any]]:
    """Detect delegation tool calls followed by clean outcomes (no correction within window)."""
    delegation_outcomes: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for i, event in enumerate(events):
        if str(event.get("event_type")) != "tool_call":
            continue
        action = str(event.get("action", "")).lower()
        if "task" not in action:
            continue

        scope = _scope_key(event.get("artifact_key"))
        if not scope:
            scope = "__delegation__"

        window = events[i + 1 : i + 30]
        had_correction = any(str(w.get("event_type")) in {"correction", "error_signature"} for w in window)
        delegation_outcomes[scope].append(
            {
                "event_id": event["id"],
                "event_time": event["event_time"],
                "clean": not had_correction,
            }
        )

    motifs: list[dict[str, Any]] = []
    for scope_key, outcomes in delegation_outcomes.items():
        clean_count = sum(1 for o in outcomes if o["clean"])
        total = len(outcomes)
        if total < min_support:
            continue
        effectiveness = clean_count / total
        if effectiveness < 0.5:
            continue
        motifs.append(
            {
                "id": f"motif:effective_delegation:{scope_key}",
                "motif_type": "effective_delegation",
                "scope_type": "delegation",
                "scope_key": scope_key,
                "pattern_signature_json": {
                    "scope_key": scope_key,
                    "total_delegations": total,
                    "clean_delegations": clean_count,
                    "effectiveness": round(effectiveness, 4),
                },
                "algorithm": "heuristic-v1",
                "support_count": total,
                "confidence": min(0.95, 0.3 + (effectiveness * 0.5)),
                "predictive_lift": round(effectiveness, 4),
                "first_seen": str(outcomes[0]["event_time"]),
                "last_seen": str(outcomes[-1]["event_time"]),
                "evidence_json": {
                    "event_ids": [o["event_id"] for o in outcomes[:20]],
                },
            }
        )
    return motifs


def _detect_convergence_patterns(
    events: list[dict[str, Any]],
    episodes: list[dict[str, Any]],
    min_support: int,
) -> list[dict[str, Any]]:
    """Detect reframe events followed by integrative/deepening episodes - collaborative emergence."""
    reframe_events = [e for e in events if str(e.get("event_type")) == "reframe"]
    if not reframe_events:
        return []

    episode_by_time = sorted(episodes, key=lambda ep: str(ep.get("start_time", "")))

    convergence_count = 0
    convergence_evidence: list[str] = []

    for reframe in reframe_events:
        reframe_time = str(reframe.get("event_time", ""))
        for episode in episode_by_time:
            ep_start = str(episode.get("start_time", ""))
            if ep_start <= reframe_time:
                continue
            if str(episode.get("dominant_character")) in {"integrative", "deepening"}:
                convergence_count += 1
                convergence_evidence.append(reframe["id"])
                break

    if convergence_count < min_support:
        return []

    total_reframes = len(reframe_events)
    convergence_rate = convergence_count / max(1, total_reframes)

    return [
        {
            "id": "motif:convergence_pattern:global",
            "motif_type": "convergence_pattern",
            "scope_type": "global",
            "scope_key": "reframe_to_synthesis",
            "pattern_signature_json": {
                "total_reframes": total_reframes,
                "followed_by_synthesis": convergence_count,
                "convergence_rate": round(convergence_rate, 4),
            },
            "algorithm": "heuristic-v1",
            "support_count": convergence_count,
            "confidence": min(0.95, 0.3 + (convergence_rate * 0.5)),
            "predictive_lift": round(convergence_rate, 4),
            "first_seen": str(reframe_events[0]["event_time"]),
            "last_seen": str(reframe_events[-1]["event_time"]),
            "evidence_json": {
                "reframe_event_ids": convergence_evidence[:20],
            },
        }
    ]


def run_mine(workspace_path: Path, min_support: int, verbose: bool) -> int:
    db_path = get_db_path(workspace_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        init_db(conn)
        events = _fetch_events(conn)
        episodes = _fetch_episodes(conn)
        if not events:
            print("no events found; nothing to mine")
            return 0

        motifs: list[dict[str, Any]] = []
        motifs.extend(_detect_corrective_loops(episodes, min_support=min_support))
        motifs.extend(_discover_cascades(events, min_support=min_support))
        motifs.extend(_predict_rework(events, min_support=min_support))
        motifs.extend(_detect_flow_states(episodes, min_support=min_support))
        motifs.extend(_detect_effective_delegations(events, min_support=min_support))
        motifs.extend(_detect_convergence_patterns(events, episodes, min_support=min_support))

        conn.execute("DELETE FROM motifs")
        conn.commit()
        changed_rows = insert_motifs(conn, motifs)

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
    print(f"episodes_seen: {len(episodes)}")
    print(f"motifs_built: {len(motifs)}")
    print(f"motifs_written_changes: {changed_rows}")
    if verbose:
        for motif in motifs[:10]:
            print(f"- {motif['motif_type']} :: {motif.get('scope_key')} (support={motif.get('support_count')})")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Mine temporal-self episodes for recurring motifs.")
    parser.add_argument("workspace_path", type=Path)
    parser.add_argument("--min-support", type=int, default=2)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    workspace_path = args.workspace_path.resolve()
    if not workspace_path.exists():
        print(f"error: workspace does not exist: {workspace_path}")
        return 2

    return run_mine(
        workspace_path=workspace_path,
        min_support=max(1, int(args.min_support)),
        verbose=bool(args.verbose),
    )


if __name__ == "__main__":
    raise SystemExit(main())

