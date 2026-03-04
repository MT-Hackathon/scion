from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def get_db_path(workspace_path: Path) -> Path:
    """Return temporal-self database path for a workspace."""
    return workspace_path / ".cursor" / ".temporal-self" / "self.db"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_dumps(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=True)


def _normalize_row_dict(row: sqlite3.Row) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in row.keys():
        value = row[key]
        if value is None:
            result[key] = None
            continue
        if key.endswith("_json") and isinstance(value, str):
            try:
                result[key] = json.loads(value)
                continue
            except json.JSONDecodeError:
                pass
        result[key] = value
    return result


def init_db(conn: sqlite3.Connection) -> None:
    """Initialize temporal-self database schema and indexes."""
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")

    conn.executescript(
        """
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    event_time TEXT NOT NULL,
    knowledge_time TEXT NOT NULL,
    strand_id TEXT NOT NULL DEFAULT 'main',
    session_id TEXT,
    attempt_id TEXT,
    event_type TEXT NOT NULL,
    action TEXT NOT NULL,
    artifact_key TEXT,
    status TEXT NOT NULL DEFAULT 'unknown',
    payload_json TEXT,
    causal_antecedent_id TEXT REFERENCES events(id),
    causal_type TEXT,
    revelation TEXT,
    episode_character TEXT,
    coherence_signal TEXT,
    confidence REAL NOT NULL DEFAULT 1.0,
    source_ref TEXT
);

CREATE TABLE IF NOT EXISTS causal_links (
    id TEXT PRIMARY KEY,
    source_event_id TEXT NOT NULL REFERENCES events(id),
    target_event_id TEXT NOT NULL REFERENCES events(id),
    link_type TEXT NOT NULL,
    pre_pivot_focus_json TEXT,
    post_pivot_focus_json TEXT,
    inferred_revelation TEXT,
    extraction_method TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0.5
);

CREATE TABLE IF NOT EXISTS decision_frames (
    id TEXT PRIMARY KEY,
    frame_type TEXT NOT NULL,
    frame_content_json TEXT NOT NULL,
    origin_episode_id TEXT REFERENCES episodes(id),
    application_count INTEGER DEFAULT 1,
    last_applied TEXT,
    validation_history_json TEXT
);

CREATE TABLE IF NOT EXISTS episodes (
    id TEXT PRIMARY KEY,
    strand_id TEXT NOT NULL DEFAULT 'main',
    parent_episode_id TEXT REFERENCES episodes(id),
    fork_from_episode_id TEXT REFERENCES episodes(id),
    merge_into_episode_id TEXT REFERENCES episodes(id),
    start_event_id TEXT REFERENCES events(id),
    end_event_id TEXT REFERENCES events(id),
    start_time TEXT NOT NULL,
    end_time TEXT,
    dominant_character TEXT NOT NULL,
    arc_type TEXT,
    causal_spine_json TEXT,
    decision_frame_id TEXT REFERENCES decision_frames(id),
    scope_key TEXT,
    change_point_score REAL,
    conformance_score REAL,
    consolidated_insight TEXT,
    utility_score REAL DEFAULT 0.0,
    retention_preference REAL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS lenses (
    id TEXT PRIMARY KEY,
    trigger_conditions_json TEXT NOT NULL,
    trigger_threshold REAL NOT NULL DEFAULT 0.5,
    reframe_type TEXT NOT NULL,
    reframe_content_json TEXT NOT NULL,
    origin_episode_id TEXT REFERENCES episodes(id),
    origin_insight TEXT,
    times_activated INTEGER DEFAULT 0,
    times_helpful INTEGER DEFAULT 0,
    times_misleading INTEGER DEFAULT 0,
    strength REAL NOT NULL DEFAULT 0.5,
    last_activated TEXT,
    status TEXT NOT NULL DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    memory_kind TEXT NOT NULL,
    scope_type TEXT,
    scope_key TEXT,
    claim TEXT NOT NULL,
    evidence_count INTEGER DEFAULT 0,
    activation_base REAL DEFAULT 0.0,
    decay_d REAL DEFAULT 0.5,
    utility_score REAL DEFAULT 0.0,
    staleness_score REAL DEFAULT 0.0,
    contradiction_count INTEGER DEFAULT 0,
    retention_preference REAL DEFAULT 0.0,
    retention_reason TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    valid_from TEXT,
    valid_to TEXT,
    supersedes_id TEXT REFERENCES memories(id)
);

CREATE TABLE IF NOT EXISTS activations (
    id TEXT PRIMARY KEY,
    memory_id TEXT NOT NULL REFERENCES memories(id),
    session_id TEXT,
    trigger_type TEXT NOT NULL,
    trigger_scope TEXT,
    rank_score REAL,
    shown_at TEXT NOT NULL,
    used_in_action INTEGER DEFAULT 0,
    feedback_label TEXT,
    outcome_delta REAL
);

CREATE TABLE IF NOT EXISTS motifs (
    id TEXT PRIMARY KEY,
    motif_type TEXT NOT NULL,
    scope_type TEXT,
    scope_key TEXT,
    pattern_signature_json TEXT NOT NULL,
    algorithm TEXT NOT NULL,
    support_count INTEGER DEFAULT 1,
    confidence REAL NOT NULL,
    predictive_lift REAL,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    evidence_json TEXT
);

CREATE TABLE IF NOT EXISTS scan_meta (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    workspace_path TEXT NOT NULL,
    last_ingest TEXT NOT NULL,
    schema_version INTEGER NOT NULL DEFAULT 1,
    sessions_analyzed INTEGER DEFAULT 0,
    events_total INTEGER DEFAULT 0,
    episodes_total INTEGER DEFAULT 0,
    memories_total INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_events_strand_time ON events(strand_id, event_time);
CREATE INDEX IF NOT EXISTS idx_events_session_time ON events(session_id, event_time);
CREATE INDEX IF NOT EXISTS idx_events_attempt_time ON events(attempt_id, event_time);
CREATE INDEX IF NOT EXISTS idx_events_type_time ON events(event_type, event_time);
CREATE INDEX IF NOT EXISTS idx_events_artifact_time ON events(artifact_key, event_time);
CREATE INDEX IF NOT EXISTS idx_causal_links_source ON causal_links(source_event_id);
CREATE INDEX IF NOT EXISTS idx_causal_links_target ON causal_links(target_event_id);
CREATE INDEX IF NOT EXISTS idx_causal_links_type ON causal_links(link_type);
CREATE INDEX IF NOT EXISTS idx_episodes_strand_start ON episodes(strand_id, start_time);
CREATE INDEX IF NOT EXISTS idx_episodes_character ON episodes(dominant_character);
CREATE INDEX IF NOT EXISTS idx_episodes_scope ON episodes(scope_key);
CREATE INDEX IF NOT EXISTS idx_decision_frames_type ON decision_frames(frame_type);
CREATE INDEX IF NOT EXISTS idx_lenses_status_strength ON lenses(status, strength DESC);
CREATE INDEX IF NOT EXISTS idx_lenses_reframe_type ON lenses(reframe_type);
CREATE INDEX IF NOT EXISTS idx_memories_scope_status ON memories(scope_key, status);
CREATE INDEX IF NOT EXISTS idx_memories_activation ON memories(activation_base DESC);
CREATE INDEX IF NOT EXISTS idx_memories_utility ON memories(utility_score DESC);
CREATE INDEX IF NOT EXISTS idx_memories_reason_status ON memories(retention_reason, status);
CREATE INDEX IF NOT EXISTS idx_activations_memory_shown ON activations(memory_id, shown_at);
CREATE INDEX IF NOT EXISTS idx_activations_session_shown ON activations(session_id, shown_at);
CREATE INDEX IF NOT EXISTS idx_motifs_type_scope ON motifs(motif_type, scope_key);
CREATE INDEX IF NOT EXISTS idx_motifs_predictive_lift ON motifs(predictive_lift DESC);
"""
    )
    conn.commit()


def insert_events(conn: sqlite3.Connection, events: list[dict[str, Any]]) -> int:
    if not events:
        return 0
    before = conn.total_changes
    rows: list[tuple[Any, ...]] = []
    for event in events:
        rows.append(
            (
                event["id"],
                event["event_time"],
                event.get("knowledge_time", _utc_now_iso()),
                event.get("strand_id", "main"),
                event.get("session_id"),
                event.get("attempt_id"),
                event["event_type"],
                event["action"],
                event.get("artifact_key"),
                event.get("status", "unknown"),
                _json_dumps(event.get("payload_json")),
                event.get("causal_antecedent_id"),
                event.get("causal_type"),
                event.get("revelation"),
                event.get("episode_character"),
                event.get("coherence_signal"),
                float(event.get("confidence", 1.0)),
                event.get("source_ref"),
            )
        )
    conn.executemany(
        """
INSERT OR IGNORE INTO events (
    id, event_time, knowledge_time, strand_id, session_id, attempt_id,
    event_type, action, artifact_key, status, payload_json, causal_antecedent_id,
    causal_type, revelation, episode_character, coherence_signal, confidence, source_ref
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""",
        rows,
    )
    conn.commit()
    return conn.total_changes - before


def insert_causal_links(conn: sqlite3.Connection, links: list[dict[str, Any]]) -> int:
    if not links:
        return 0
    before = conn.total_changes
    rows: list[tuple[Any, ...]] = []
    for link in links:
        rows.append(
            (
                link["id"],
                link["source_event_id"],
                link["target_event_id"],
                link["link_type"],
                _json_dumps(link.get("pre_pivot_focus_json")),
                _json_dumps(link.get("post_pivot_focus_json")),
                link.get("inferred_revelation"),
                link.get("extraction_method", "heuristic"),
                float(link.get("confidence", 0.5)),
            )
        )
    conn.executemany(
        """
INSERT OR IGNORE INTO causal_links (
    id, source_event_id, target_event_id, link_type, pre_pivot_focus_json,
    post_pivot_focus_json, inferred_revelation, extraction_method, confidence
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
""",
        rows,
    )
    conn.commit()
    return conn.total_changes - before


def insert_episodes(conn: sqlite3.Connection, episodes: list[dict[str, Any]]) -> int:
    if not episodes:
        return 0
    before = conn.total_changes
    rows: list[tuple[Any, ...]] = []
    for episode in episodes:
        rows.append(
            (
                episode["id"],
                episode.get("strand_id", "main"),
                episode.get("parent_episode_id"),
                episode.get("fork_from_episode_id"),
                episode.get("merge_into_episode_id"),
                episode.get("start_event_id"),
                episode.get("end_event_id"),
                episode["start_time"],
                episode.get("end_time"),
                episode["dominant_character"],
                episode.get("arc_type"),
                _json_dumps(episode.get("causal_spine_json")),
                episode.get("decision_frame_id"),
                episode.get("scope_key"),
                episode.get("change_point_score"),
                episode.get("conformance_score"),
                episode.get("consolidated_insight"),
                float(episode.get("utility_score", 0.0)),
                float(episode.get("retention_preference", 0.0)),
            )
        )
    conn.executemany(
        """
INSERT INTO episodes (
    id, strand_id, parent_episode_id, fork_from_episode_id, merge_into_episode_id,
    start_event_id, end_event_id, start_time, end_time, dominant_character, arc_type,
    causal_spine_json, decision_frame_id, scope_key, change_point_score, conformance_score,
    consolidated_insight, utility_score, retention_preference
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(id) DO UPDATE SET
    strand_id = excluded.strand_id,
    parent_episode_id = excluded.parent_episode_id,
    fork_from_episode_id = excluded.fork_from_episode_id,
    merge_into_episode_id = excluded.merge_into_episode_id,
    start_event_id = excluded.start_event_id,
    end_event_id = excluded.end_event_id,
    start_time = excluded.start_time,
    end_time = excluded.end_time,
    dominant_character = excluded.dominant_character,
    arc_type = excluded.arc_type,
    causal_spine_json = excluded.causal_spine_json,
    decision_frame_id = excluded.decision_frame_id,
    scope_key = excluded.scope_key,
    change_point_score = excluded.change_point_score,
    conformance_score = excluded.conformance_score,
    consolidated_insight = excluded.consolidated_insight,
    utility_score = excluded.utility_score,
    retention_preference = excluded.retention_preference
""",
        rows,
    )
    conn.commit()
    return conn.total_changes - before


def insert_motifs(conn: sqlite3.Connection, motifs: list[dict[str, Any]]) -> int:
    if not motifs:
        return 0
    before = conn.total_changes
    rows: list[tuple[Any, ...]] = []
    for motif in motifs:
        rows.append(
            (
                motif["id"],
                motif["motif_type"],
                motif.get("scope_type"),
                motif.get("scope_key"),
                _json_dumps(motif.get("pattern_signature_json", {})) or "{}",
                motif.get("algorithm", "heuristic"),
                int(motif.get("support_count", 1)),
                float(motif.get("confidence", 0.5)),
                motif.get("predictive_lift"),
                motif.get("first_seen", _utc_now_iso()),
                motif.get("last_seen", _utc_now_iso()),
                _json_dumps(motif.get("evidence_json")),
            )
        )
    conn.executemany(
        """
INSERT INTO motifs (
    id, motif_type, scope_type, scope_key, pattern_signature_json, algorithm, support_count,
    confidence, predictive_lift, first_seen, last_seen, evidence_json
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(id) DO UPDATE SET
    motif_type = excluded.motif_type,
    scope_type = excluded.scope_type,
    scope_key = excluded.scope_key,
    pattern_signature_json = excluded.pattern_signature_json,
    algorithm = excluded.algorithm,
    support_count = excluded.support_count,
    confidence = excluded.confidence,
    predictive_lift = excluded.predictive_lift,
    first_seen = excluded.first_seen,
    last_seen = excluded.last_seen,
    evidence_json = excluded.evidence_json
""",
        rows,
    )
    conn.commit()
    return conn.total_changes - before


def upsert_lens(conn: sqlite3.Connection, lens: dict[str, Any]) -> None:
    conn.execute(
        """
INSERT INTO lenses (
    id, trigger_conditions_json, trigger_threshold, reframe_type, reframe_content_json,
    origin_episode_id, origin_insight, times_activated, times_helpful, times_misleading,
    strength, last_activated, status
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(id) DO UPDATE SET
    trigger_conditions_json = excluded.trigger_conditions_json,
    trigger_threshold = excluded.trigger_threshold,
    reframe_type = excluded.reframe_type,
    reframe_content_json = excluded.reframe_content_json,
    origin_episode_id = excluded.origin_episode_id,
    origin_insight = excluded.origin_insight,
    times_activated = excluded.times_activated,
    times_helpful = excluded.times_helpful,
    times_misleading = excluded.times_misleading,
    strength = excluded.strength,
    last_activated = excluded.last_activated,
    status = excluded.status
""",
        (
            lens["id"],
            _json_dumps(lens.get("trigger_conditions_json", {})) or "{}",
            float(lens.get("trigger_threshold", 0.5)),
            lens["reframe_type"],
            _json_dumps(lens.get("reframe_content_json", {})) or "{}",
            lens.get("origin_episode_id"),
            lens.get("origin_insight"),
            int(lens.get("times_activated", 0)),
            int(lens.get("times_helpful", 0)),
            int(lens.get("times_misleading", 0)),
            float(lens.get("strength", 0.5)),
            lens.get("last_activated"),
            lens.get("status", "active"),
        ),
    )
    conn.commit()


def upsert_memory(conn: sqlite3.Connection, memory: dict[str, Any]) -> None:
    conn.execute(
        """
INSERT INTO memories (
    id, memory_kind, scope_type, scope_key, claim, evidence_count, activation_base, decay_d,
    utility_score, staleness_score, contradiction_count, retention_preference,
    retention_reason, status, valid_from, valid_to, supersedes_id
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(id) DO UPDATE SET
    memory_kind = excluded.memory_kind,
    scope_type = excluded.scope_type,
    scope_key = excluded.scope_key,
    claim = excluded.claim,
    evidence_count = excluded.evidence_count,
    activation_base = excluded.activation_base,
    decay_d = excluded.decay_d,
    utility_score = excluded.utility_score,
    staleness_score = excluded.staleness_score,
    contradiction_count = excluded.contradiction_count,
    retention_preference = excluded.retention_preference,
    retention_reason = excluded.retention_reason,
    status = excluded.status,
    valid_from = excluded.valid_from,
    valid_to = excluded.valid_to,
    supersedes_id = excluded.supersedes_id
""",
        (
            memory["id"],
            memory["memory_kind"],
            memory.get("scope_type"),
            memory.get("scope_key"),
            memory["claim"],
            int(memory.get("evidence_count", 0)),
            float(memory.get("activation_base", 0.0)),
            float(memory.get("decay_d", 0.5)),
            float(memory.get("utility_score", 0.0)),
            float(memory.get("staleness_score", 0.0)),
            int(memory.get("contradiction_count", 0)),
            float(memory.get("retention_preference", 0.0)),
            memory.get("retention_reason"),
            memory.get("status", "active"),
            memory.get("valid_from"),
            memory.get("valid_to"),
            memory.get("supersedes_id"),
        ),
    )
    conn.commit()


def insert_activation(conn: sqlite3.Connection, activation: dict[str, Any]) -> None:
    conn.execute(
        """
INSERT INTO activations (
    id, memory_id, session_id, trigger_type, trigger_scope, rank_score, shown_at,
    used_in_action, feedback_label, outcome_delta
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(id) DO UPDATE SET
    memory_id = excluded.memory_id,
    session_id = excluded.session_id,
    trigger_type = excluded.trigger_type,
    trigger_scope = excluded.trigger_scope,
    rank_score = excluded.rank_score,
    shown_at = excluded.shown_at,
    used_in_action = excluded.used_in_action,
    feedback_label = excluded.feedback_label,
    outcome_delta = excluded.outcome_delta
""",
        (
            activation["id"],
            activation["memory_id"],
            activation.get("session_id"),
            activation["trigger_type"],
            activation.get("trigger_scope"),
            activation.get("rank_score"),
            activation.get("shown_at", _utc_now_iso()),
            int(activation.get("used_in_action", 0)),
            activation.get("feedback_label"),
            activation.get("outcome_delta"),
        ),
    )
    conn.commit()


def get_active_lenses(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM lenses WHERE status = ? ORDER BY strength DESC, id ASC",
        ("active",),
    ).fetchall()
    return [_normalize_row_dict(row) for row in rows]


def get_memories_by_scope(
    conn: sqlite3.Connection,
    scope_key: str,
    status: str = "active",
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
SELECT * FROM memories
WHERE scope_key = ? AND status = ?
ORDER BY utility_score DESC, activation_base DESC, id ASC
""",
        (scope_key, status),
    ).fetchall()
    return [_normalize_row_dict(row) for row in rows]


def get_rework_risk(conn: sqlite3.Connection, scope_key: str) -> dict[str, Any] | None:
    row = conn.execute(
        """
SELECT * FROM motifs
WHERE motif_type = 'rework_prediction' AND scope_key = ?
ORDER BY predictive_lift DESC, last_seen DESC
LIMIT 1
""",
        (scope_key,),
    ).fetchone()
    if row is None:
        return None
    return _normalize_row_dict(row)


def get_recent_episodes(conn: sqlite3.Connection, limit: int = 10) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
SELECT * FROM episodes
ORDER BY start_time DESC, id DESC
LIMIT ?
""",
        (max(1, int(limit)),),
    ).fetchall()
    return [_normalize_row_dict(row) for row in rows]


def upsert_scan_meta(
    conn: sqlite3.Connection,
    workspace_path: Path,
    sessions: int,
    events: int,
    episodes: int,
    memories: int,
) -> None:
    conn.execute(
        """
INSERT INTO scan_meta (
    id, workspace_path, last_ingest, schema_version, sessions_analyzed,
    events_total, episodes_total, memories_total
) VALUES (1, ?, ?, 1, ?, ?, ?, ?)
ON CONFLICT(id) DO UPDATE SET
    workspace_path = excluded.workspace_path,
    last_ingest = excluded.last_ingest,
    sessions_analyzed = excluded.sessions_analyzed,
    events_total = excluded.events_total,
    episodes_total = excluded.episodes_total,
    memories_total = excluded.memories_total
""",
        (
            workspace_path.as_posix(),
            _utc_now_iso(),
            int(sessions),
            int(events),
            int(episodes),
            int(memories),
        ),
    )
    conn.commit()


def clear_derived(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM activations")
    conn.execute("DELETE FROM memories")
    conn.execute("DELETE FROM decision_frames")
    conn.execute("DELETE FROM lenses")
    conn.execute("DELETE FROM motifs")
    conn.execute("DELETE FROM episodes")
    conn.commit()

