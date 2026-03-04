# pyright: reportMissingImports=false
from __future__ import annotations

import os
import re
import sys
from pathlib import Path, PurePosixPath
from typing import NamedTuple

from .complexity import ComplexityMetrics
from .scanner import SourceFile
from .structural import CentralityMetrics
from .test_mapping import TestLink


class RiskHotspot(NamedTuple):
    path: str
    max_cyclomatic: int
    churn_30d: int
    risk_product: int
    unsafe_count: int
    has_tests: bool
    pagerank_pct: int


def compute_hotspots(
    complexity: dict[str, ComplexityMetrics],
    commit_counts: dict[str, int],
    test_links: dict[str, TestLink],
    centrality: dict[str, CentralityMetrics],
    source_files: list[SourceFile] | None = None,
    top_n: int = 5,
) -> list[RiskHotspot]:
    if top_n <= 0 or not complexity:
        return []

    pagerank_pct = _percentile_map({path: metrics.pagerank for path, metrics in centrality.items()})
    repo_prefixes = _repo_prefixes(commit_counts)
    source_lookup: dict[str, Path] = {}
    if source_files:
        source_lookup = {source_file.path: source_file.abs_path for source_file in source_files}
    hotspots: list[RiskHotspot] = []

    for path, metrics in complexity.items():
        if _looks_like_test(path):
            continue

        churn = _resolve_churn(path, commit_counts, repo_prefixes)
        test_link = test_links.get(path)
        has_tests = test_link.has_tests if test_link is not None else False
        max_cyclomatic = max(0, int(metrics.max_cyclomatic))
        unsafe_path = source_lookup.get(path) or _resolve_abs_path(path)
        unsafe_count = _count_unsafe(unsafe_path, metrics.language)
        risk_product = (max_cyclomatic * churn) + (unsafe_count * 20)

        hotspots.append(
            RiskHotspot(
                path=path,
                max_cyclomatic=max_cyclomatic,
                churn_30d=churn,
                risk_product=risk_product,
                unsafe_count=unsafe_count,
                has_tests=has_tests,
                pagerank_pct=int(pagerank_pct.get(path, 0)),
            )
        )

    hotspots.sort(
        key=lambda hotspot: (
            hotspot.risk_product,
            hotspot.max_cyclomatic,
            hotspot.churn_30d,
            hotspot.pagerank_pct,
        ),
        reverse=True,
    )
    return hotspots[:top_n]


def _resolve_churn(path: str, commit_counts: dict[str, int], repo_prefixes: set[str]) -> int:
    candidates = _churn_candidates(path, repo_prefixes)
    for candidate in candidates:
        if candidate in commit_counts:
            return max(0, int(commit_counts[candidate]))

    _warn_unmatched(path)
    return 0


def _churn_candidates(path: str, repo_prefixes: set[str]) -> list[str]:
    normalized = path.replace("\\", "/")
    parts = normalized.split("/")
    stripped = "/".join(parts[1:]) if len(parts) > 1 else normalized

    candidates: list[str] = []
    for candidate in (normalized, stripped):
        if candidate and candidate not in candidates:
            candidates.append(candidate)

    for repo in sorted(repo_prefixes):
        for candidate in (normalized, stripped):
            if not candidate:
                continue
            prefixed = f"{repo}/{candidate}"
            if prefixed not in candidates:
                candidates.append(prefixed)

    return candidates


def _repo_prefixes(commit_counts: dict[str, int]) -> set[str]:
    prefixes: set[str] = set()
    for path in commit_counts:
        parts = path.replace("\\", "/").split("/")
        if len(parts) > 1 and parts[0]:
            prefixes.add(parts[0])
    return prefixes


def _percentile_map(values: dict[str, float]) -> dict[str, int]:
    if not values:
        return {}
    ordered = sorted(values.items(), key=lambda item: item[1])
    if len(ordered) == 1:
        return {ordered[0][0]: 100}

    denominator = len(ordered) - 1
    percentile: dict[str, int] = {}
    for index, (path, _) in enumerate(ordered):
        percentile[path] = round((index / denominator) * 100)
    return percentile


def _looks_like_test(path: str) -> bool:
    normalized = f"/{path.replace('\\', '/').lower()}/"
    if any(marker in normalized for marker in ("/test/", "/tests/", "/__tests__/", "/spec/")):
        return True
    name = PurePosixPath(path).name.lower()
    return (
        ".test." in name
        or ".spec." in name
        or name.startswith("test_")
        or "_test." in name
    )


def _warn_unmatched(path: str) -> None:
    if not _is_verbose():
        return
    print(f"[risk warning] no churn match for {path}", file=sys.stderr)


def _is_verbose() -> bool:
    value = os.getenv("CODEBASE_SENSE_VERBOSE", "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _count_unsafe(abs_path: Path | None, language: str) -> int:
    if language != "rust" or abs_path is None:
        return 0
    try:
        content = abs_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return 0
    return len(re.findall(r"unsafe\s*[{\s]|unsafe\s+fn\b", content))


def _resolve_abs_path(path: str) -> Path | None:
    normalized = Path(path)
    if normalized.exists():
        return normalized.resolve()

    cwd_candidate = (Path.cwd() / path).resolve()
    if cwd_candidate.exists():
        return cwd_candidate

    parent_candidate = (Path.cwd().parent / path).resolve()
    if parent_candidate.exists():
        return parent_candidate

    return None
