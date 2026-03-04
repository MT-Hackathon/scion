#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# pyright: reportMissingImports=false
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from lib.cache import get_active_lenses, get_db_path, get_recent_episodes, init_db


def _render_lines(conn: sqlite3.Connection, workspace_path: Path) -> list[str]:
    events_total = conn.execute("SELECT COUNT(*) AS c FROM events").fetchone()["c"]
    episodes_total = conn.execute("SELECT COUNT(*) AS c FROM episodes").fetchone()["c"]
    motifs_total = conn.execute("SELECT COUNT(*) AS c FROM motifs").fetchone()["c"]
    memories_total = conn.execute("SELECT COUNT(*) AS c FROM memories").fetchone()["c"]

    episode_char_rows = conn.execute(
        """
SELECT dominant_character, COUNT(*) AS c
FROM episodes
GROUP BY dominant_character
ORDER BY c DESC
"""
    ).fetchall()
    episode_character_counts = [(row["dominant_character"], row["c"]) for row in episode_char_rows]

    rework_rows = conn.execute(
        """
SELECT scope_key, support_count, confidence, predictive_lift, last_seen
FROM motifs
WHERE motif_type = 'rework_prediction'
ORDER BY predictive_lift DESC, confidence DESC
LIMIT 10
"""
    ).fetchall()

    cascade_rows = conn.execute(
        """
SELECT scope_key, support_count, confidence, last_seen
FROM motifs
WHERE motif_type = 'cascade_discovery'
ORDER BY support_count DESC, confidence DESC
LIMIT 10
"""
    ).fetchall()

    positive_rows = conn.execute(
        """
SELECT motif_type, scope_key, support_count, confidence, predictive_lift, last_seen
FROM motifs
WHERE motif_type IN ('flow_state', 'effective_delegation', 'convergence_pattern')
ORDER BY motif_type, support_count DESC, confidence DESC
LIMIT 15
"""
    ).fetchall()

    teaching_rows = conn.execute(
        """
SELECT event_type, action, payload_json, event_time, source_ref
FROM events
WHERE event_type IN ('teaching', 'calibration')
ORDER BY event_time DESC
LIMIT 15
"""
    ).fetchall()

    endorsement_rows = conn.execute(
        """
SELECT artifact_key, COUNT(*) AS c, MAX(event_time) AS last_seen
FROM events
WHERE event_type = 'endorsement'
GROUP BY artifact_key
ORDER BY c DESC
LIMIT 10
"""
    ).fetchall()

    arc_rows = conn.execute(
        """
SELECT e.session_id, ep.dominant_character, ep.start_time
FROM episodes ep
JOIN events e ON e.id = ep.start_event_id
WHERE e.session_id IS NOT NULL
ORDER BY e.session_id, ep.start_time ASC
"""
    ).fetchall()

    scan_meta = conn.execute("SELECT * FROM scan_meta WHERE id = 1").fetchone()
    recent_episodes = get_recent_episodes(conn, limit=10)
    active_lenses = get_active_lenses(conn)

    lines: list[str] = []
    lines.append("## Temporal-Self Diagnostic Signals")
    lines.append("")
    lines.append(
        f"Generated: {datetime.now(timezone.utc).isoformat()} | Workspace: `{workspace_path.as_posix()}`"
    )
    lines.append("")
    lines.append("### Cache Totals")
    lines.append(f"- events: {events_total}")
    lines.append(f"- episodes: {episodes_total}")
    lines.append(f"- motifs: {motifs_total}")
    lines.append(f"- memories: {memories_total}")
    lines.append("")

    if scan_meta:
        lines.append("### Last Scan Meta")
        lines.append(f"- last_ingest: {scan_meta['last_ingest']}")
        lines.append(f"- sessions_analyzed: {scan_meta['sessions_analyzed']}")
        lines.append(f"- events_total: {scan_meta['events_total']}")
        lines.append(f"- episodes_total: {scan_meta['episodes_total']}")
        lines.append("")

    lines.append("### Episode Character Distribution")
    if not episode_character_counts:
        lines.append("- no episodes available")
    else:
        for character, count in episode_character_counts:
            lines.append(f"- {character}: {count}")
    lines.append("")

    lines.append("### Recent Episodes")
    if not recent_episodes:
        lines.append("- no recent episodes")
    else:
        for episode in recent_episodes:
            lines.append(
                "- "
                f"{episode.get('id')} | {episode.get('dominant_character')} | "
                f"scope={episode.get('scope_key') or 'n/a'} | "
                f"start={episode.get('start_time')}"
            )
    lines.append("")

    lines.append("### Teaching & Calibration Signals")
    if not teaching_rows:
        lines.append("- none detected")
    else:
        for row in teaching_rows:
            event_type = row["event_type"]
            payload = row["payload_json"]
            text_preview = ""
            if payload:
                try:
                    parsed = json.loads(payload) if isinstance(payload, str) else payload
                    raw_text = parsed.get("text", "")
                    text_preview = raw_text[:120].replace("\n", " ").strip()
                    if len(raw_text) > 120:
                        text_preview += "..."
                except (json.JSONDecodeError, AttributeError):
                    text_preview = "(unparseable)"
            lines.append(f"- [{event_type}] {text_preview}")
    lines.append("")

    lines.append("### Endorsement Patterns")
    if not endorsement_rows:
        lines.append("- none detected")
    else:
        for row in endorsement_rows:
            scope = row["artifact_key"] or "general"
            lines.append(f"- {scope} | endorsed {row['c']}x | last={row['last_seen']}")
    lines.append("")

    session_arcs: dict[str, list[str]] = {}
    for row in arc_rows:
        sid = str(row["session_id"])
        char = str(row["dominant_character"])
        session_arcs.setdefault(sid, []).append(char)

    lines.append("### Session Arcs (character trajectories)")
    if not session_arcs:
        lines.append("- no sessions with episodes")
    else:
        shown = 0
        for sid, chars in sorted(session_arcs.items(), reverse=True):
            if shown >= 10:
                break
            arc_str = " -> ".join(chars)
            short_sid = sid[:12] if len(sid) > 12 else sid
            lines.append(f"- {short_sid}: {arc_str}")
            shown += 1
    lines.append("")

    lines.append("### Rework Predictions")
    if not rework_rows:
        lines.append("- none")
    else:
        for row in rework_rows:
            lines.append(
                "- "
                f"{row['scope_key']} | support={row['support_count']} | "
                f"lift={row['predictive_lift']} | conf={row['confidence']} | "
                f"last={row['last_seen']}"
            )
    lines.append("")

    lines.append("### Cascades (Non-Tooling)")
    if not cascade_rows:
        lines.append("- none")
    else:
        for row in cascade_rows:
            lines.append(
                "- "
                f"{row['scope_key']} | support={row['support_count']} | "
                f"conf={row['confidence']} | last={row['last_seen']}"
            )
    lines.append("")

    lines.append("### Positive Motifs")
    if not positive_rows:
        lines.append("- none detected")
    else:
        for row in positive_rows:
            lines.append(
                "- "
                f"{row['motif_type']} :: {row['scope_key']} | "
                f"support={row['support_count']} | "
                f"lift={row['predictive_lift']} | "
                f"conf={row['confidence']} | "
                f"last={row['last_seen']}"
            )
    lines.append("")

    lines.append("### Active Lenses")
    if not active_lenses:
        lines.append("- none")
    else:
        for lens in active_lenses[:10]:
            lines.append(
                "- "
                f"{lens.get('id')} | type={lens.get('reframe_type')} | "
                f"strength={lens.get('strength')} | status={lens.get('status')}"
            )
    lines.append("")
    lines.append("_Diagnostic only. Portrait authoring is manual in rule 998._")
    return lines


def run_portrait(workspace_path: Path, max_lines: int, verbose: bool) -> int:
    db_path = get_db_path(workspace_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        init_db(conn)
        lines = _render_lines(conn, workspace_path)
    finally:
        conn.close()

    max_lines = max(5, int(max_lines))
    if len(lines) > max_lines:
        lines = lines[: max_lines - 1] + ["... (truncated)"]

    output = "\n".join(lines).rstrip() + "\n"
    if verbose:
        print(f"[portrait] db={db_path} lines={len(lines)}", flush=True)
    print(output, end="")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Render temporal-self diagnostics (not authored portrait).")
    parser.add_argument("workspace_path", type=Path)
    parser.add_argument("--max-lines", type=int, default=50)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    workspace_path = args.workspace_path.resolve()
    if not workspace_path.exists():
        print(f"error: workspace does not exist: {workspace_path}")
        return 2

    return run_portrait(
        workspace_path=workspace_path,
        max_lines=args.max_lines,
        verbose=bool(args.verbose),
    )


if __name__ == "__main__":
    raise SystemExit(main())

