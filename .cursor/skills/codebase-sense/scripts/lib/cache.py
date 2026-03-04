# pyright: reportMissingImports=false
from __future__ import annotations

import json
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from . import scanner

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS scan_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

_EXCLUDED_DIRS = {
    "node_modules",
    ".angular",
    "dist",
    "build",
    "out",
    "target",
    ".git",
    ".idea",
    ".vscode",
    ".cursor",
    ".claude",
    "__pycache__",
}


def get_cache_path(workspace_path: Path) -> Path:
    cache_dir = workspace_path.resolve() / ".cursor" / ".codebase-sense"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / "cache.db"


def is_cache_fresh(workspace_path: Path, max_age_hours: float = 4.0) -> bool:
    cache_path = get_cache_path(workspace_path)
    if not cache_path.exists():
        return False

    last_scan = load_meta(workspace_path, "last_scan_epoch")
    prior_file_count = load_meta(workspace_path, "file_count")
    prior_heads = load_meta(workspace_path, "repo_heads")

    if not last_scan or not prior_file_count or not prior_heads:
        return False

    try:
        age_hours = (datetime.now(timezone.utc).timestamp() - float(last_scan)) / 3600.0
    except (TypeError, ValueError):
        return False
    if age_hours > max_age_hours:
        return False

    repos = scanner.discover_repos(workspace_path.resolve())
    current_file_count = _count_candidate_files(repos)

    try:
        previous_count = int(prior_file_count)
    except ValueError:
        return False

    denominator = max(1, previous_count)
    delta_ratio = abs(current_file_count - previous_count) / denominator
    if delta_ratio > 0.05:
        return False

    current_heads = _get_repo_heads(repos)
    try:
        previous_heads = json.loads(prior_heads)
    except json.JSONDecodeError:
        return False

    return previous_heads == current_heads


def get_cached_scan_time(workspace_path: Path) -> float | None:
    raw_epoch = load_meta(workspace_path, "last_scan_epoch")
    if raw_epoch is None:
        return None

    try:
        last_scan_epoch = float(raw_epoch)
    except ValueError:
        return None

    elapsed_seconds = datetime.now(timezone.utc).timestamp() - last_scan_epoch
    return max(0.0, elapsed_seconds / 3600.0)


def save_meta(workspace_path: Path, key: str, value: str) -> None:
    cache_path = get_cache_path(workspace_path)
    with sqlite3.connect(cache_path) as connection:
        _ensure_schema(connection)
        connection.execute(
            """
            INSERT INTO scan_meta (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
            """,
            (key, value, datetime.now(timezone.utc).isoformat()),
        )
        connection.commit()


def load_meta(workspace_path: Path, key: str) -> str | None:
    cache_path = get_cache_path(workspace_path)
    if not cache_path.exists():
        return None

    with sqlite3.connect(cache_path) as connection:
        _ensure_schema(connection)
        row = connection.execute("SELECT value FROM scan_meta WHERE key = ?", (key,)).fetchone()
        if row is None:
            return None
        return str(row[0])


def _ensure_schema(connection: sqlite3.Connection) -> None:
    connection.execute(_SCHEMA_SQL)


def _count_candidate_files(repos: list[Path]) -> int:
    count = 0
    for repo in repos:
        stack = [repo.resolve()]
        while stack:
            current = stack.pop()
            try:
                children = list(current.iterdir())
            except OSError:
                continue

            for child in children:
                if child.is_dir():
                    if child.name in _EXCLUDED_DIRS:
                        continue
                    stack.append(child)
                    continue
                if scanner.is_supported_file(child):
                    count += 1
    return count


def _get_repo_heads(repos: list[Path]) -> dict[str, str]:
    heads: dict[str, str] = {}
    for repo in repos:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            heads[repo.name] = result.stdout.strip()
    return heads
