#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = ["networkx>=3.2", "numpy>=1.26", "tree-sitter>=0.23", "tree-sitter-typescript>=0.23", "tree-sitter-python>=0.23", "tree-sitter-rust>=0.23"]
# ///
# pyright: reportMissingImports=false
from __future__ import annotations

import argparse
import json
import math
import statistics
import subprocess
import sys
import tomllib
from collections import defaultdict
from typing import NamedTuple
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import lib.behavioral as behavioral  # noqa: E402
import lib.cache as cache  # noqa: E402
import lib.complexity as complexity  # noqa: E402
import lib.divergence as divergence  # noqa: E402
from lib.helpers import classify  # noqa: E402
import lib.risk as risk  # noqa: E402
import lib.scanner as scanner  # noqa: E402
import lib.structural as structural  # noqa: E402
import lib.test_mapping as test_mapping  # noqa: E402

_STACK_DETECTORS: list[tuple[frozenset[str], str]] = [
    (frozenset({"angular.json"}), "angular"),
    (frozenset({"svelte.config.js", "svelte.config.ts"}), "sveltekit"),
    (frozenset({"build.gradle", "build.gradle.kts", "pom.xml"}), "spring-boot"),
    (frozenset({"pyproject.toml", "setup.py", "requirements.txt"}), "python"),
    (frozenset({"tsconfig.json"}), "typescript"),
    (frozenset({"Cargo.toml"}), "rust"),
]


def main() -> int:
    args = _parse_args()
    workspace_path = args.workspace_path.resolve()
    max_lines = max(20, args.max_lines)

    if cache.is_cache_fresh(workspace_path):
        cached = cache.load_meta(workspace_path, "briefing_markdown")
        if cached:
            print(cached)
            return 0

    repos = [workspace_path]
    files: list[scanner.SourceFile] = []

    graph = None
    connected_node_count = 0
    centrality: dict[str, structural.CentralityMetrics] = {}
    communities: list[set[str]] = []
    boundary_alignment = 100.0
    drift_files: list[structural.DriftFile] = []

    commits: list[behavioral.Commit] = []
    commit_heat: dict[str, dict[int, int]] = {}
    cochange: dict[tuple[str, str], int] = {}
    cascade_predictions: list[behavioral.CascadePrediction] = []
    change_adjacency: dict[str, list[tuple[str, float]]] = {}
    commit_counts: dict[str, int] = {}
    complexity_metrics: dict[str, complexity.ComplexityMetrics] = {}
    test_links: dict[str, test_mapping.TestLink] = {}
    hotspots: list[risk.RiskHotspot] = []

    divergence_alerts: list[divergence.DivergenceAlert] = []

    if not args.this_repo_only:
        try:
            repos = scanner.discover_repos(workspace_path)
        except Exception as exc:
            _warn(f"repo discovery failed: {exc}")
            repos = [workspace_path]

    try:
        files = scanner.scan_files(repos)
    except Exception as exc:
        _warn(f"file scan failed: {exc}")
        files = []

    try:
        graph = structural.build_dependency_graph(files)
    except Exception as exc:
        _warn(f"structural graph failed: {exc}")
        graph = None

    if graph is not None:
        connected_nodes = {str(node) for edge in graph.edges() for node in edge}
        connected_node_count = len(connected_nodes)
        try:
            centrality = structural.compute_centrality(graph)
        except Exception as exc:
            _warn(f"centrality failed: {exc}")
            centrality = {}

        try:
            communities = structural.detect_communities(graph)
        except Exception as exc:
            _warn(f"community detection failed: {exc}")
            communities = []

        try:
            boundary_alignment, drift_files = structural.compute_boundary_alignment(communities)
        except Exception as exc:
            _warn(f"boundary alignment failed: {exc}")
            boundary_alignment, drift_files = 100.0, []

    for repo in repos:
        try:
            commits.extend(behavioral.parse_git_log(repo, since_days=15))
        except Exception as exc:
            _warn(f"git analysis failed for {repo.name}: {exc}")

    try:
        commit_heat = behavioral.compute_commit_heat(commits, windows=[1, 5, 15])
        cochange = behavioral.build_cochange_matrix(commits)
        commit_counts = _compute_commit_counts(commits)
        cascade_predictions = behavioral.compute_cascade_predictions(
            cochange, commit_counts, top_n=5, min_evidence=3, total_commits=len(commits)
        )
        change_adjacency = behavioral.compute_change_adjacency(commits)
    except Exception as exc:
        _warn(f"behavioral analysis failed: {exc}")
        commit_heat = {}
        cochange = {}
        commit_counts = {}
        cascade_predictions = []
        change_adjacency = {}

    try:
        complexity_metrics = complexity.analyze_files(files)
    except Exception as exc:
        _warn(f"complexity analysis failed: {exc}")
        complexity_metrics = {}

    try:
        test_links = test_mapping.map_tests_to_sources(files)
    except Exception as exc:
        _warn(f"test mapping failed: {exc}")
        test_links = {}

    try:
        hotspots = risk.compute_hotspots(
            complexity=complexity_metrics,
            commit_counts=commit_counts,
            test_links=test_links,
            centrality=centrality,
            top_n=5,
        )
    except Exception as exc:
        _warn(f"risk computation failed: {exc}")
        hotspots = []

    try:
        divergence.set_source_file_index({source_file.path: source_file.abs_path for source_file in files})
        structural_ranks = {path: metrics.pagerank for path, metrics in centrality.items()}
        in_degree: dict[str, int] = {}
        if graph is not None:
            for _, target in graph.edges():
                key = str(target)
                in_degree[key] = in_degree.get(key, 0) + 1
        divergence_alerts = divergence.compute_divergence(
            structural_ranks, commit_counts, in_degree=in_degree
        )
    except Exception as exc:
        _warn(f"divergence analysis failed: {exc}")
        divergence_alerts = []

    scan_timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%MZ")
    stack, crate_count = _detect_stack(repos)
    branch_name = _get_branch_name(workspace_path)
    heat_thresholds = _compute_heat_thresholds(commit_heat, len(commits))

    previous_snapshot_raw = cache.load_meta(workspace_path, "briefing_state_v1")
    previous_snapshot: dict | None = None
    if previous_snapshot_raw:
        try:
            previous_snapshot = json.loads(previous_snapshot_raw)
        except (json.JSONDecodeError, TypeError):
            previous_snapshot = None

    text, current_snapshot = _format_briefing(
        workspace_path=workspace_path,
        repos=repos,
        files=files,
        centrality=centrality,
        hotspots=hotspots,
        commit_heat=commit_heat,
        cascade_predictions=cascade_predictions,
        divergence_alerts=divergence_alerts,
        boundary_alignment=boundary_alignment,
        communities=communities,
        drift_files=drift_files,
        connected_node_count=connected_node_count,
        change_adjacency=change_adjacency,
        commit_counts=commit_counts,
        test_links=test_links,
        stack=stack,
        crate_count=crate_count,
        scan_timestamp=scan_timestamp,
        max_lines=max_lines,
        branch_name=branch_name,
        heat_thresholds=heat_thresholds,
        previous_snapshot=previous_snapshot,
    )

    _save_cache(workspace_path, repos, len(files), text, current_snapshot)
    print(text)
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate codebase proprioception briefing.")
    parser.add_argument("workspace_path", type=Path, help="Path to workspace root.")
    parser.add_argument(
        "--this-repo-only",
        action="store_true",
        help="Only scan the provided workspace repository; skip sibling repo discovery.",
    )
    parser.add_argument("--max-lines", type=int, default=120, help="Maximum lines in output.")
    return parser.parse_args()


def _format_briefing(
    workspace_path: Path,
    repos: list[Path],
    files: list[scanner.SourceFile],
    centrality: dict[str, structural.CentralityMetrics],
    hotspots: list[risk.RiskHotspot],
    commit_heat: dict[str, dict[int, int]],
    cascade_predictions: list[behavioral.CascadePrediction],
    divergence_alerts: list[divergence.DivergenceAlert],
    boundary_alignment: float,
    communities: list[set[str]],
    drift_files: list[structural.DriftFile],
    connected_node_count: int,
    change_adjacency: dict[str, list[tuple[str, float]]],
    commit_counts: dict[str, int],
    test_links: dict[str, test_mapping.TestLink],
    stack: str,
    crate_count: int | None,
    scan_timestamp: str,
    max_lines: int,
    branch_name: str = "",
    heat_thresholds: HeatThresholds | None = None,
    previous_snapshot: dict | None = None,
) -> tuple[str, dict]:
    repo_name = workspace_path.name

    stack_line_parts = [f"Stack: {stack}"]
    if crate_count is not None:
        stack_line_parts.append(f"{crate_count} crates")
    stack_line_parts.append(f"{len(repos)} repos")
    stack_line_parts.append(f"{len(files)} source files")

    header_label = f"{repo_name} | {branch_name}" if branch_name else repo_name
    header_lines = [
        f"## Codebase Briefing | {header_label} | {scan_timestamp}",
        " | ".join(stack_line_parts),
    ]

    thresholds = heat_thresholds if heat_thresholds is not None else _compute_heat_thresholds(commit_heat, 0)

    structural_lines = _format_structural_core(centrality, files)
    risk_lines = _format_risk_hotspots(hotspots)
    active_lines = _format_active_zones(commit_heat, thresholds, file_count=len(files))
    cascade_lines = _format_cascade(cascade_predictions)
    divergence_lines = _format_divergence(divergence_alerts)
    boundary_lines = _format_boundary(
        boundary_alignment, communities, drift_files, connected_node_count=connected_node_count
    )
    guidance_lines = _format_guidance(
        files=files,
        centrality=centrality,
        commit_counts=commit_counts,
        commit_heat=commit_heat,
        change_adjacency=change_adjacency,
        test_links=test_links,
        thresholds=thresholds,
    )

    current_snapshot = _build_briefing_snapshot(
        hotspots, commit_heat, cascade_predictions, thresholds,
    )
    delta_lines = _format_delta(current_snapshot, previous_snapshot)

    sections = {
        "structural": structural_lines,
        "risk": risk_lines,
        "active": active_lines,
        "delta": delta_lines,
        "cascade": cascade_lines,
        "divergence": divergence_lines,
        "boundary": boundary_lines,
        "guidance": guidance_lines,
    }
    order = ["structural", "risk", "active", "delta", "cascade", "divergence", "boundary", "guidance"]
    include = set(order)
    if not delta_lines:
        include.discard("delta")

    composed = _compose_lines(header_lines, sections, order, include)
    if len(composed) > max_lines:
        for removable in ["boundary", "divergence", "guidance", "delta", "cascade"]:
            include.discard(removable)
            composed = _compose_lines(header_lines, sections, order, include)
            if len(composed) <= max_lines:
                break

    if len(composed) > max_lines:
        composed = composed[:max_lines]

    return "\n".join(composed), current_snapshot


def _compose_lines(
    header_lines: list[str],
    sections: dict[str, list[str]],
    order: list[str],
    include: set[str],
) -> list[str]:
    lines = list(header_lines)
    for name in order:
        if name not in include:
            continue
        lines.append("")
        lines.extend(sections[name])
    return lines


def _format_structural_core(
    centrality: dict[str, structural.CentralityMetrics], files: list[scanner.SourceFile]
) -> list[str]:
    file_loc = {source_file.path: source_file.loc for source_file in files}
    top_files = sorted(
        centrality.items(),
        key=lambda item: item[1].pagerank,
        reverse=True,
    )[:10]

    lines = ["### Evidence: Structural Core (top 10 PageRank)"]
    if not top_files:
        lines.append("  (no structural data)")
        return lines

    for path, metrics in top_files:
        lines.append(
            f"  {path} (PR:{metrics.pagerank:.4f}, {metrics.classification}) {file_loc.get(path, 0)} LOC"
        )
    return lines


def _format_risk_hotspots(hotspots: list[risk.RiskHotspot]) -> list[str]:
    lines = ["### Risk: Complexity Hotspots (churn * complexity, top 5)"]
    if not hotspots:
        lines.append("  (insufficient data)")
        return lines
    for hotspot in hotspots:
        test_label = "YES" if hotspot.has_tests else "NO !!"
        parts = PurePosixPath(hotspot.path).parts
        name = "/".join(parts[-2:]) if len(parts) >= 2 else hotspot.path
        lines.append(
            f"  {name} | cx={hotspot.max_cyclomatic} | churn={hotspot.churn_30d} "
            f"| risk={hotspot.risk_product} | tests: {test_label}"
        )
    return lines


def _format_active_zones(
    commit_heat: dict[str, dict[int, int]],
    thresholds: HeatThresholds,
    file_count: int = 0,
) -> list[str]:
    lines = ["### Evidence: Active Zones (1d/5d/15d by module)"]
    if not commit_heat:
        lines.append("  (no behavioral data)")
        return lines

    cap = 5 if file_count < 100 else 10

    ranked = sorted(
        commit_heat.items(),
        key=lambda item: (-item[1].get(15, 0), -item[1].get(5, 0), -item[1].get(1, 0), item[0]),
    )

    shown = 0
    for module, counts in ranked:
        label = _heat_label(counts, thresholds)
        if label == "stable":
            continue
        lines.append(
            f"  {module}: {counts.get(1, 0)}/{counts.get(5, 0)}/{counts.get(15, 0)} [{label}]"
        )
        shown += 1
        if shown >= cap:
            break

    if shown == 0:
        lines.append("  (all modules stable)")

    return lines


def _format_cascade(cascade_predictions: list[behavioral.CascadePrediction]) -> list[str]:
    lines = ["### Inference: Cascade Predictions (top 5 chains, 15d window)"]
    if not cascade_predictions:
        lines.append("  (no cascade data)")
        return lines

    for prediction in cascade_predictions[:5]:
        trigger = _strip_repo_prefix(prediction.trigger)
        targets = ", ".join(
            f"{_strip_repo_prefix(target)} ({min(1.0, probability):.0%})"
            for target, probability in prediction.targets
        )
        lines.append(f"  {trigger} -> {targets}")
    return lines


def _format_divergence(divergence_alerts: list[divergence.DivergenceAlert]) -> list[str]:
    lines = ["### Inference: Divergence Alerts (top debt + top stable-or-dead)"]

    debt = sorted(
        [alert for alert in divergence_alerts if alert.category == "DEBT"],
        key=lambda alert: alert.behavioral_pct,
        reverse=True,
    )[:3]
    stable = sorted(
        [alert for alert in divergence_alerts if alert.category == "STABLE-OR-DEAD"],
        key=lambda alert: alert.structural_pct,
        reverse=True,
    )[:3]

    selected = debt + stable
    if not selected:
        lines.append("  (no divergence alerts)")
        return lines

    for alert in selected:
        lines.append(
            f"  {alert.category}: {alert.path} - structural {alert.structural_pct}th / behavioral {alert.behavioral_pct}th -> {alert.message}"
        )
    return lines


def _format_boundary(
    boundary_alignment: float,
    communities: list[set[str]],
    drift_files: list[structural.DriftFile],
    connected_node_count: int = 0,
) -> list[str]:
    lines = ["### Inference: Boundary Health"]

    if connected_node_count < 30:
        lines.append("  (insufficient graph density for reliable boundary analysis)")
        return lines

    label = classify(boundary_alignment, [(90, "healthy"), (75, "watch")], "drifted")
    lines.append(
        f"  Alignment: {boundary_alignment:.1f}% ({label}) | {len(communities)} communities"
    )

    for drift in drift_files[:3]:
        lines.append(
            f"  DRIFT: {drift.path} (community {drift.community_id}, directory {drift.expected_dir})"
        )

    return lines


def _format_guidance(
    files: list[scanner.SourceFile],
    centrality: dict[str, structural.CentralityMetrics],
    commit_counts: dict[str, int],
    commit_heat: dict[str, dict[int, int]],
    change_adjacency: dict[str, list[tuple[str, float]]],
    test_links: dict[str, test_mapping.TestLink],
    thresholds: HeatThresholds,
) -> list[str]:
    module_totals, module_test_files = _module_test_counts(files)
    module_gap = {
        module: _test_gap_score(module_totals.get(module, 0), module_test_files.get(module, 0))
        for module in module_totals
    }

    structural_pct = _percentile_from_values({path: metrics.pagerank for path, metrics in centrality.items()})
    behavioral_pct = _percentile_from_values({path: float(count) for path, count in commit_counts.items()})

    risk_scores: list[tuple[str, float]] = []
    for source_file in files:
        module = _module_path(source_file.path)
        gap_pct = module_gap.get(module, 1.0) * 100.0
        score = statistics.mean(
            [
                float(structural_pct.get(source_file.path, 0)),
                float(behavioral_pct.get(source_file.path, 0)),
                gap_pct,
            ]
        ) / 100.0
        risk_scores.append((source_file.path, score))

    risk_scores.sort(key=lambda item: item[1], reverse=True)
    highest_risk = risk_scores[:3]

    active_modules = {
        module
        for module, counts in commit_heat.items()
        if _heat_label(counts, thresholds) in {"hot", "active"}
    }
    test_gap_candidates: list[tuple[str, float]] = []
    for module in active_modules:
        if _is_test_module(module):
            continue
        stripped = _strip_repo_prefix(module)
        gap = module_gap.get(stripped) if stripped != module else None
        if gap is None:
            gap = module_gap.get(module)
        if gap is None:
            continue
        test_gap_candidates.append((module, gap))
    test_gap_active = sorted(test_gap_candidates, key=lambda item: item[1], reverse=True)[:3]

    adjacency_watch: list[tuple[str, str, float]] = []
    for module, neighbors in change_adjacency.items():
        if not neighbors:
            continue
        target, probability = neighbors[0]
        adjacency_watch.append((module, target, min(1.0, probability)))
    adjacency_watch.sort(key=lambda item: item[2], reverse=True)
    adjacency_watch = adjacency_watch[:3]

    lines = ["### Action: Session Guidance"]
    if highest_risk:
        risk_text = ", ".join(f"{path} ({score:.4f})" for path, score in highest_risk)
    else:
        risk_text = "n/a"
    lines.append(f"  - Highest-risk targets: {risk_text}")

    if test_gap_active:
        gap_text = ", ".join(f"{module} ({gap:.3f})" for module, gap in test_gap_active)
    else:
        gap_text = "n/a"
    lines.append(f"  - Test gaps in active code: {gap_text}")

    if adjacency_watch:
        adjacency_text = ", ".join(
            f"{_strip_repo_prefix(module)} -> {_strip_repo_prefix(target)} ({probability:.0%})"
            for module, target, probability in adjacency_watch
        )
    else:
        adjacency_text = "n/a"
    lines.append(f"  - Change adjacency watch: {adjacency_text}")
    lines.extend(_format_untested_core(centrality, test_links))

    return lines


def _format_untested_core(
    centrality: dict[str, structural.CentralityMetrics],
    test_links: dict[str, test_mapping.TestLink],
) -> list[str]:
    top_core = sorted(
        centrality.items(),
        key=lambda item: item[1].pagerank,
        reverse=True,
    )[:10]
    if not top_core:
        return ["  - Untested structural core: n/a"]

    untested = [
        path
        for path, _ in top_core
        if not test_mapping.is_test_file(path)
        and not test_links.get(
            path,
            test_mapping.TestLink(source_path=path, test_paths=(), has_tests=False, evidence="none"),
        ).has_tests
    ]
    if not untested:
        return ["  - Untested structural core: none"]

    return [f"  - Untested structural core (top PR): {', '.join(untested)}"]


def _build_briefing_snapshot(
    hotspots: list[risk.RiskHotspot],
    commit_heat: dict[str, dict[int, int]],
    cascade_predictions: list[behavioral.CascadePrediction],
    thresholds: HeatThresholds,
) -> dict:
    snapshot_hotspots = [
        {"path": h.path, "risk": h.risk_product, "has_tests": h.has_tests}
        for h in hotspots[:10]
    ]

    heat_labels: dict[str, str] = {}
    for module, counts in commit_heat.items():
        label = _heat_label(counts, thresholds)
        if label != "stable":
            heat_labels[module] = label

    cascades: list[dict] = []
    for prediction in cascade_predictions[:5]:
        for target, probability in prediction.targets:
            cascades.append({
                "trigger": prediction.trigger,
                "target": target,
                "probability": round(probability, 3),
            })

    return {
        "version": 1,
        "generated_at_epoch": datetime.now(UTC).timestamp(),
        "hotspots": snapshot_hotspots,
        "heat_labels": heat_labels,
        "cascades": cascades[:15],
    }


def _compute_delta(current: dict, previous: dict) -> list[tuple[str, str]]:
    events: list[tuple[str, str]] = []

    prev_risks = {h["path"]: h for h in previous.get("hotspots", [])}
    for hotspot in current.get("hotspots", []):
        prev = prev_risks.get(hotspot["path"])
        if prev and abs(hotspot["risk"] - prev["risk"]) >= 12:
            direction = "+" if hotspot["risk"] > prev["risk"] else "-"
            delta = hotspot["risk"] - prev["risk"]
            parts = PurePosixPath(hotspot["path"]).parts
            short = "/".join(parts[-2:]) if len(parts) >= 2 else hotspot["path"]
            events.append(("risk", f"{short} risk: {prev['risk']} → {hotspot['risk']} ({direction}{abs(delta)})"))
        elif prev is None and hotspot["risk"] >= 35:
            parts = PurePosixPath(hotspot["path"]).parts
            short = "/".join(parts[-2:]) if len(parts) >= 2 else hotspot["path"]
            events.append(("risk", f"{short} entered risk hotspots (risk={hotspot['risk']})"))

    prev_labels = previous.get("heat_labels", {})
    curr_labels = current.get("heat_labels", {})
    all_modules = set(prev_labels) | set(curr_labels)
    for module in sorted(all_modules):
        prev_label = prev_labels.get(module, "stable")
        curr_label = curr_labels.get(module, "stable")
        if prev_label != curr_label:
            events.append(("heat", f"{_strip_repo_prefix(module)}: {prev_label} → {curr_label}"))

    prev_cascade_keys = {
        (c["trigger"], c["target"]) for c in previous.get("cascades", [])
    }
    for cascade in current.get("cascades", []):
        key = (cascade["trigger"], cascade["target"])
        if key not in prev_cascade_keys and cascade["probability"] >= 0.5:
            t_parts = PurePosixPath(cascade["trigger"]).parts
            d_parts = PurePosixPath(cascade["target"]).parts
            t_short = "/".join(t_parts[-2:]) if len(t_parts) >= 2 else cascade["trigger"]
            d_short = "/".join(d_parts[-2:]) if len(d_parts) >= 2 else cascade["target"]
            events.append(("cascade", f"New cascade: {t_short} → {d_short} ({cascade['probability']:.0%})"))

    return events


_DELTA_CATEGORY_CAPS = {"risk": 2, "heat": 2, "cascade": 1}
_DELTA_MAX_LINES = 6


def _format_delta(current_snapshot: dict, previous_snapshot: dict | None) -> list[str]:
    if previous_snapshot is None:
        return []

    prev_version = previous_snapshot.get("version")
    if prev_version != 1:
        return []

    prev_epoch = previous_snapshot.get("generated_at_epoch", 0)
    age_hours = (datetime.now(UTC).timestamp() - prev_epoch) / 3600.0
    if age_hours > 72:
        return []

    events = _compute_delta(current_snapshot, previous_snapshot)
    if not events:
        return [
            "### Delta: Since Last Analysis",
            "  No material movement in tracked signals.",
        ]

    selected: list[str] = []
    category_counts: dict[str, int] = defaultdict(int)
    for category, text in events:
        cap = _DELTA_CATEGORY_CAPS.get(category, 2)
        if category_counts[category] >= cap:
            continue
        if len(selected) >= _DELTA_MAX_LINES:
            break
        selected.append(text)
        category_counts[category] += 1

    age_label = f"{age_hours:.0f}h ago"
    if age_hours > 24:
        age_label += ", stale baseline"

    lines = [f"### Delta: Since Last Analysis ({age_label})"]
    for item in selected:
        lines.append(f"  - {item}")
    return lines


def _module_test_counts(
    files: list[scanner.SourceFile],
) -> tuple[dict[str, int], dict[str, int]]:
    module_totals: dict[str, int] = defaultdict(int)
    module_test_files: dict[str, int] = defaultdict(int)

    for source_file in files:
        module = _module_path(source_file.path)
        module_totals[module] += 1
        lower_path = source_file.path.lower()
        if "test" in lower_path or "spec" in lower_path:
            module_test_files[module] += 1

    return dict(module_totals), dict(module_test_files)


_TEST_DIR_SEGMENTS = frozenset({"test", "tests", "__tests__", "spec", "__test__"})


def _is_test_module(module: str) -> bool:
    parts = PurePosixPath(module).parts
    return bool(set(parts) & _TEST_DIR_SEGMENTS)


def _module_path(path: str) -> str:
    parent = PurePosixPath(path).parent
    return parent.as_posix() if parent.as_posix() != "." else path


def _test_gap_score(total_files: int, test_files: int) -> float:
    if total_files <= 0:
        return 1.0
    ratio = test_files / total_files
    return max(0.0, 1.0 - min(1.0, ratio * 2.0))


def _percentile_from_values(values: dict[str, float]) -> dict[str, int]:
    if not values:
        return {}
    ordered = sorted(values.items(), key=lambda item: item[1])
    if len(ordered) == 1:
        key = ordered[0][0]
        return {key: 100}

    denominator = len(ordered) - 1
    percentiles: dict[str, int] = {}
    for index, (key, _) in enumerate(ordered):
        percentiles[key] = round((index / denominator) * 100)
    return percentiles


class HeatThresholds(NamedTuple):
    active_5: int
    hot_5: int
    active_15: int
    hot_15: int


def _compute_heat_thresholds(
    commit_heat: dict[str, dict[int, int]],
    total_commits: int,
) -> HeatThresholds:
    v5 = sorted(c.get(5, 0) for c in commit_heat.values() if c.get(5, 0) > 0)
    v15 = sorted(c.get(15, 0) for c in commit_heat.values() if c.get(15, 0) > 0)

    active_15_floor = 1 if total_commits <= 7 else 2

    active_15 = max(active_15_floor, _nth_percentile(v15, 0.50))
    hot_15 = max(3, _nth_percentile(v15, 0.80), active_15 + 1)

    active_5 = max(1, _nth_percentile(v5, 0.50)) if v5 else 1
    hot_5 = max(2, _nth_percentile(v5, 0.80), active_5 + 1) if v5 else 2

    if commit_heat:
        any_active = any(
            c.get(15, 0) >= active_15 or c.get(5, 0) >= active_5
            for c in commit_heat.values()
        )
        if not any_active:
            active_15, active_5 = 1, 1

    return HeatThresholds(
        active_5=active_5, hot_5=hot_5, active_15=active_15, hot_15=hot_15,
    )


def _nth_percentile(sorted_values: list[int], q: float) -> int:
    if not sorted_values:
        return 0
    idx = max(0, math.ceil(len(sorted_values) * q) - 1)
    return sorted_values[idx]


def _heat_label(counts: dict[int, int], thresholds: HeatThresholds) -> str:
    c5 = counts.get(5, 0)
    c15 = counts.get(15, 0)

    if (c15 >= thresholds.hot_15 and c5 >= thresholds.hot_5) or c15 >= thresholds.hot_15 + 2:
        return "hot"
    if c15 >= thresholds.active_15 or c5 >= thresholds.active_5:
        return "active"
    return "stable"


def _compute_commit_counts(commits: list[behavioral.Commit]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for commit in commits:
        for path in {change.path for change in commit.files}:
            counts[path] += 1
    return dict(counts)


def _detect_stack(repos: list[Path]) -> tuple[str, int | None]:
    frameworks: list[str] = []
    markers = _collect_markers(repos, max_depth=2)

    for marker_set, label in _STACK_DETECTORS:
        if any(marker in markers for marker in marker_set):
            frameworks.append(label)
    if "package.json" in markers and "sveltekit" not in frameworks:
        frameworks.append("node")

    crate_count = _detect_cargo_workspace_crates(repos) if "Cargo.toml" in markers else None
    stack = ", ".join(frameworks) if frameworks else "unknown"
    return stack, crate_count


def _detect_cargo_workspace_crates(repos: list[Path]) -> int | None:
    for repo in repos:
        cargo_toml = repo / "Cargo.toml"
        if not cargo_toml.is_file():
            continue
        try:
            parsed = tomllib.loads(cargo_toml.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
            continue
        workspace = parsed.get("workspace")
        if not isinstance(workspace, dict):
            continue
        members = workspace.get("members")
        if isinstance(members, list):
            count = 0
            for member in members:
                if isinstance(member, str):
                    expanded = list(repo.glob(member))
                    count += len(expanded) if expanded else 1
            return count
        return 0
    return None


def _collect_markers(repos: list[Path], max_depth: int = 2) -> set[str]:
    marker_names = {
        "angular.json", "package.json", "svelte.config.js", "svelte.config.ts",
        "build.gradle", "build.gradle.kts", "pom.xml",
        "pyproject.toml", "setup.py", "requirements.txt", "tsconfig.json", "Cargo.toml",
    }
    found: set[str] = set()
    for repo in repos:
        _scan_markers(repo, marker_names, found, depth=0, max_depth=max_depth)
    return found


def _scan_markers(
    directory: Path, marker_names: set[str], found: set[str], depth: int, max_depth: int
) -> None:
    if depth > max_depth:
        return
    try:
        for child in directory.iterdir():
            if child.name in marker_names and child.is_file():
                found.add(child.name)
            elif child.is_dir() and child.name not in {
                "node_modules", ".git", "dist", "build", ".venv", "venv", "__pycache__"
            }:
                _scan_markers(child, marker_names, found, depth + 1, max_depth)
    except OSError:
        pass


def _strip_repo_prefix(path: str) -> str:
    parts = path.split("/", 1)
    return parts[1] if len(parts) > 1 else path


def _save_cache(
    workspace_path: Path, repos: list[Path], file_count: int, text: str,
    snapshot: dict | None = None,
) -> None:
    now_epoch = datetime.now(UTC).timestamp()
    cache.save_meta(workspace_path, "last_scan_epoch", str(now_epoch))
    cache.save_meta(workspace_path, "file_count", str(file_count))
    cache.save_meta(workspace_path, "repo_heads", json.dumps(_repo_heads(repos), sort_keys=True))
    cache.save_meta(workspace_path, "briefing_markdown", text)
    if snapshot is not None:
        cache.save_meta(workspace_path, "briefing_state_v1", json.dumps(snapshot, sort_keys=True))


def _repo_heads(repos: list[Path]) -> dict[str, str]:
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


def _get_branch_name(workspace_path: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=workspace_path,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return result.stdout.strip()
    return ""


def _warn(message: str) -> None:
    print(f"[briefing warning] {message}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
