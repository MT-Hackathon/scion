# pyright: reportMissingImports=false
from __future__ import annotations

import itertools
import subprocess
from collections import defaultdict, namedtuple
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

Commit = namedtuple("Commit", ["hash", "timestamp", "author", "files"])
FileChange = namedtuple("FileChange", ["status", "path"])
CascadePrediction = namedtuple("CascadePrediction", ["trigger", "targets"])

_BEHAVIORAL_SKIP_MARKERS = (
    ".cursor/",
    ".claude/",
    ".github/",
    ".gitlab/",
    "node_modules/",
    ".vscode/",
    ".idea/",
    ".aiassistant/",
)


def parse_git_log(repo_path: Path, since_days: int = 15) -> list[Commit]:
    command = [
        "git",
        "log",
        f"--since={since_days}.days.ago",
        "--name-status",
        "--no-merges",
        "--pretty=format:COMMIT|%H|%aI|%an",
    ]
    result = subprocess.run(
        command,
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return []

    commits: list[Commit] = []
    current_hash = ""
    current_time = ""
    current_author = ""
    current_files: list[FileChange] = []
    repo_name = repo_path.name

    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("COMMIT|"):
            if current_hash:
                commits.append(
                    Commit(
                        hash=current_hash,
                        timestamp=current_time,
                        author=current_author,
                        files=current_files,
                    )
                )

            parts = line.split("|", 3)
            current_hash = parts[1] if len(parts) > 1 else ""
            current_time = parts[2] if len(parts) > 2 else ""
            current_author = parts[3] if len(parts) > 3 else ""
            current_files = []
            continue

        fields = raw_line.split("\t")
        if len(fields) < 2:
            continue

        status_token = fields[0].strip()
        status = status_token[0] if status_token else "M"
        if status not in {"A", "M", "D"}:
            status = "M"

        relative_path = fields[-1].strip().replace("\\", "/")
        full_path = f"{repo_name}/{relative_path}"
        if not _is_behavioral_path(full_path):
            continue

        current_files.append(FileChange(status=status, path=full_path))

    if current_hash:
        commits.append(
            Commit(hash=current_hash, timestamp=current_time, author=current_author, files=current_files)
        )

    return commits


def compute_commit_heat(
    commits: list[Commit], windows: list[int] = [1, 5, 15]
) -> dict[str, dict[int, int]]:
    now = datetime.now(timezone.utc)
    ordered_windows = sorted(windows)
    heat: dict[str, dict[int, int]] = defaultdict(lambda: {window: 0 for window in ordered_windows})

    for commit in commits:
        commit_time = _parse_timestamp(commit.timestamp)
        age_days = (now - commit_time).total_seconds() / 86400.0

        modules = {_module_path(change.path) for change in commit.files}
        for module in modules:
            for window in ordered_windows:
                if age_days <= window:
                    heat[module][window] += 1

    return dict(heat)


def build_cochange_matrix(commits: list[Commit]) -> dict[tuple[str, str], int]:
    cochange: dict[tuple[str, str], int] = defaultdict(int)

    for commit in commits:
        files = sorted(
            {change.path for change in commit.files if _is_behavioral_path(change.path)}
        )
        if len(files) < 2 or len(files) > 8:
            continue

        for left, right in itertools.combinations(files, 2):
            pair = (left, right) if left < right else (right, left)
            cochange[pair] += 1

    return dict(cochange)


def compute_cascade_predictions(
    cochange: dict[tuple[str, str], int],
    commit_counts: dict[str, int],
    top_n: int = 5,
    min_evidence: int = 3,
    total_commits: int = 0,
) -> list[CascadePrediction]:
    ubiquity_threshold = max(1, int(total_commits * 0.4)) if total_commits > 0 else 0
    ubiquitous = {
        path
        for path, count in commit_counts.items()
        if ubiquity_threshold > 0 and count >= ubiquity_threshold
    }

    related: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for (left, right), count in cochange.items():
        if count < min_evidence:
            continue
        if left in ubiquitous or right in ubiquitous:
            continue
        related[left][right] += count
        related[right][left] += count

    scored: list[tuple[float, CascadePrediction]] = []
    for trigger, targets in related.items():
        baseline = max(1, commit_counts.get(trigger, 0))
        target_probs: list[tuple[str, float]] = []

        for target, count in targets.items():
            probability = min(1.0, count / baseline)
            target_probs.append((target, probability))

        if not target_probs:
            continue

        target_probs.sort(key=lambda item: item[1], reverse=True)
        top_targets = target_probs[:3]
        max_probability = top_targets[0][1]
        scored.append((max_probability, CascadePrediction(trigger=trigger, targets=top_targets)))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [prediction for _, prediction in scored[:top_n]]


def compute_change_adjacency(commits: list[Commit]) -> dict[str, list[tuple[str, float]]]:
    module_counts: dict[str, int] = defaultdict(int)
    module_pairs: dict[tuple[str, str], int] = defaultdict(int)

    for commit in commits:
        modules = sorted({_module_path(change.path) for change in commit.files if _is_behavioral_path(change.path)})
        if not modules:
            continue

        for module in modules:
            module_counts[module] += 1

        for left, right in itertools.combinations(modules, 2):
            pair = (left, right) if left < right else (right, left)
            module_pairs[pair] += 1

    adjacency: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for (left, right), count in module_pairs.items():
        left_base = max(1, module_counts[left])
        right_base = max(1, module_counts[right])
        adjacency[left].append((right, min(1.0, count / left_base)))
        adjacency[right].append((left, min(1.0, count / right_base)))

    for module, neighbors in adjacency.items():
        neighbors.sort(key=lambda item: item[1], reverse=True)
        adjacency[module] = neighbors[:5]

    return dict(adjacency)


def _module_path(file_path: str) -> str:
    parent = PurePosixPath(file_path).parent
    return parent.as_posix() if parent.as_posix() != "." else file_path


def _parse_timestamp(value: str) -> datetime:
    if not value:
        return datetime.now(timezone.utc)

    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _is_behavioral_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return not any(marker in normalized for marker in _BEHAVIORAL_SKIP_MARKERS)
