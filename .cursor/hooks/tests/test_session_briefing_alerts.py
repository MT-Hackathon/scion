#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = ["pytest"]
# ///
"""Tests for session_briefing.py alert injection functions."""
from __future__ import annotations

import importlib.util
import io
import json
import sqlite3
import sys
import time
from pathlib import Path

# Load the module under test
_HOOK_PATH = Path(__file__).resolve().parents[1] / "session_briefing.py"
spec = importlib.util.spec_from_file_location("session_briefing", _HOOK_PATH)
assert spec and spec.loader
_mod = importlib.util.module_from_spec(spec)
_original_stdin = sys.stdin
try:
    # session_briefing resolves paths by reading hook payload from stdin on import.
    sys.stdin = io.StringIO("{}")
    spec.loader.exec_module(_mod)
finally:
    sys.stdin = _original_stdin


def _make_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS notifications (
            id TEXT PRIMARY KEY,
            severity TEXT NOT NULL DEFAULT 'info',
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            context_json TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            delivered_at TEXT,
            archived_at TEXT
        )
    """
    )
    conn.commit()
    conn.close()
    return db_path


class TestQueryPendingNotifications:
    def test_returns_empty_on_missing_table(self, tmp_path):
        db_path = tmp_path / "empty.db"
        conn = sqlite3.connect(str(db_path))
        conn.close()
        result = _mod._query_pending_notifications(db_path)
        assert result == []

    def test_returns_pending_rows(self, tmp_path):
        db_path = _make_db(tmp_path)
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "INSERT INTO notifications (id, severity, category, title, body) VALUES (?,?,?,?,?)",
            ("n1", "warning", "sync", "Stale sync", "Pull needed"),
        )
        conn.commit()
        conn.close()

        rows = _mod._query_pending_notifications(db_path)
        assert len(rows) == 1
        assert rows[0][3] == "Stale sync"

    def test_excludes_delivered_rows(self, tmp_path):
        db_path = _make_db(tmp_path)
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "INSERT INTO notifications (id, severity, category, title, body, delivered_at) "
            "VALUES (?,?,?,?,?, datetime('now'))",
            ("n1", "info", "sync", "Already delivered", "body"),
        )
        conn.commit()
        conn.close()
        rows = _mod._query_pending_notifications(db_path)
        assert rows == []


class TestCheckStalenessFromState:
    def test_returns_empty_when_no_state_file(self, tmp_path):
        rows = _mod._check_staleness_from_state(tmp_path)
        assert rows == []

    def test_returns_empty_when_recent_pull(self, tmp_path):
        state = {"last_pull": {"commit": "abc", "timestamp": str(int(time.time()))}}
        (tmp_path / ".graft.state.json").write_text(json.dumps(state), encoding="utf-8")
        rows = _mod._check_staleness_from_state(tmp_path)
        assert rows == []

    def test_returns_alert_when_stale(self, tmp_path):
        old_ts = int(time.time()) - (10 * 86_400)  # 10 days ago
        state = {"last_pull": {"commit": "abc", "timestamp": str(old_ts)}}
        (tmp_path / ".graft.state.json").write_text(json.dumps(state), encoding="utf-8")
        rows = _mod._check_staleness_from_state(tmp_path)
        assert len(rows) == 1
        assert rows[0][1] == "warning"
        assert rows[0][2] == "sync"

    def test_handles_legacy_canonical_commit_key(self, tmp_path):
        old_ts = int(time.time()) - (8 * 86_400)
        state = {"last_pull": {"canonical_commit": "abc", "timestamp": str(old_ts)}}
        (tmp_path / ".graft.state.json").write_text(json.dumps(state), encoding="utf-8")
        rows = _mod._check_staleness_from_state(tmp_path)
        assert len(rows) == 1


class TestFormatAlertsPrefix:
    def test_empty_rows_returns_empty_string(self):
        result = _mod._format_alerts_prefix([])
        assert result == ""

    def test_formats_single_row(self):
        rows = [("id1", "warning", "sync", "Stale", "Body text")]
        result = _mod._format_alerts_prefix(rows)
        assert "Rootstock Alerts" in result
        assert "warning · sync" in result
        assert "Stale" in result
        assert "Body text" in result


class TestMarkNotificationsDelivered:
    def test_marks_delivered(self, tmp_path):
        db_path = _make_db(tmp_path)
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "INSERT INTO notifications (id, severity, category, title, body) VALUES (?,?,?,?,?)",
            ("n1", "info", "sync", "T", "B"),
        )
        conn.commit()
        conn.close()

        _mod._mark_notifications_delivered(db_path, ["n1"])

        conn = sqlite3.connect(str(db_path))
        row = conn.execute("SELECT delivered_at FROM notifications WHERE id='n1'").fetchone()
        conn.close()
        assert row[0] is not None

    def test_empty_ids_is_noop(self, tmp_path):
        db_path = _make_db(tmp_path)
        _mod._mark_notifications_delivered(db_path, [])  # must not raise

    def test_skips_synthetic_empty_id(self, tmp_path):
        db_path = _make_db(tmp_path)
        _mod._mark_notifications_delivered(db_path, ["", ""])  # must not raise or error


class TestArchiveOldNotifications:
    def test_archives_old_delivered_rows(self, tmp_path):
        db_path = _make_db(tmp_path)
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "INSERT INTO notifications (id, severity, category, title, body, delivered_at) "
            "VALUES ('old1','info','sync','T','B', datetime('now', '-10 days'))",
        )
        conn.commit()
        conn.close()

        _mod._archive_old_notifications(db_path, days=7)

        conn = sqlite3.connect(str(db_path))
        row = conn.execute("SELECT archived_at FROM notifications WHERE id='old1'").fetchone()
        conn.close()
        assert row[0] is not None
