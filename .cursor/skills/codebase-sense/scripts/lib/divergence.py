# pyright: reportMissingImports=false
from __future__ import annotations

import re
from collections import namedtuple
from pathlib import Path

DivergenceAlert = namedtuple(
    "DivergenceAlert",
    ["path", "category", "structural_pct", "behavioral_pct", "message"],
)

_RE_EXPORT_RE = re.compile(r"^\s*export\s+.+\s+from\s+[\"'].+[\"']\s*;?\s*$")
_SOURCE_FILE_INDEX: dict[str, Path] = {}
_INFRA_PATTERNS = {
    ".gitlab-ci.yml", ".github/workflows", "Makefile", "Dockerfile",
    "docker-compose.yml", "Jenkinsfile",
}
_INFRA_SUFFIXES = {".toml", ".cfg", ".ini", ".yml", ".yaml"}
_CONFIG_NAMES = {
    "pyproject.toml", "setup.py", "setup.cfg", "package.json", "package-lock.json",
    "tsconfig.json", "angular.json", "pom.xml", "build.gradle", "build.gradle.kts",
    "svelte.config.js", "svelte.config.ts", "vite.config.ts", "vite.config.js",
}
_ARCHETYPE_MESSAGES: dict[str, str] = {
    "config": "config churn - check dependency stability",
    "infra": "infrastructure churn - expected if actively evolving CI/deploy",
}


def set_source_file_index(source_file_index: dict[str, Path]) -> None:
    _SOURCE_FILE_INDEX.clear()
    _SOURCE_FILE_INDEX.update(source_file_index)


def compute_divergence(
    structural_ranks: dict[str, float],
    behavioral_ranks: dict[str, int],
    in_degree: dict[str, int] | None = None,
) -> list[DivergenceAlert]:
    all_paths = set(structural_ranks) | set(behavioral_ranks)
    if not all_paths:
        return []

    structural_values = {path: float(structural_ranks.get(path, 0.0)) for path in all_paths}
    behavioral_values = {path: float(behavioral_ranks.get(path, 0)) for path in all_paths}

    structural_pct = _percentile_map(structural_values)
    behavioral_pct = _percentile_map(behavioral_values)

    alerts: list[DivergenceAlert] = []
    for path in sorted(all_paths):
        s_pct = structural_pct[path]
        b_pct = behavioral_pct[path]

        if s_pct >= 75 and b_pct >= 75:
            alerts.append(
                DivergenceAlert(
                    path=path,
                    category="CORE",
                    structural_pct=s_pct,
                    behavioral_pct=b_pct,
                    message="healthy: important and active",
                )
            )
            continue

        if s_pct < 50 and b_pct >= 75:
            archetype = _classify_archetype(path)
            message = _ARCHETYPE_MESSAGES.get(archetype, "logic may be in wrong layer")
            alerts.append(
                DivergenceAlert(
                    path=path,
                    category="DEBT",
                    structural_pct=s_pct,
                    behavioral_pct=b_pct,
                    message=message,
                )
            )
            continue

        if s_pct >= 75 and b_pct < 25:
            if _is_barrel(path):
                continue
            file_in_degree = (in_degree or {}).get(path, 0)
            if file_in_degree >= 3:
                continue
            alerts.append(
                DivergenceAlert(
                    path=path,
                    category="STABLE-OR-DEAD",
                    structural_pct=s_pct,
                    behavioral_pct=b_pct,
                    message="verify or remove",
                )
            )

    return alerts


def _percentile_map(values: dict[str, float]) -> dict[str, int]:
    ordered = sorted(values.items(), key=lambda item: item[1])
    if not ordered:
        return {}

    if len(ordered) == 1:
        only_path = ordered[0][0]
        return {only_path: 100}

    percentile: dict[str, int] = {}
    denominator = len(ordered) - 1
    for index, (path, _) in enumerate(ordered):
        pct = int(round((index / denominator) * 100))
        percentile[path] = pct
    return percentile


def _classify_archetype(path: str) -> str:
    name = path.rsplit("/", 1)[-1] if "/" in path else path
    if name in _CONFIG_NAMES:
        return "config"
    for pattern in _INFRA_PATTERNS:
        if pattern in path:
            return "infra"
    suffix = "." + name.rsplit(".", 1)[-1] if "." in name else ""
    if name.startswith(".") and suffix in _INFRA_SUFFIXES:
        return "infra"
    return "source"


def _is_barrel(path: str) -> bool:
    normalized = path.replace("\\", "/")
    if normalized.endswith("/index.ts") or normalized.endswith("/index.js"):
        return True

    source_path = _SOURCE_FILE_INDEX.get(normalized)
    if source_path is None or not source_path.exists():
        return False

    try:
        content = source_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False

    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not lines:
        return False

    re_exports = sum(1 for line in lines if _RE_EXPORT_RE.match(line))
    return (re_exports / len(lines)) > 0.8
