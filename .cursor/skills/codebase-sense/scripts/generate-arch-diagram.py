#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = ["networkx>=3.0", "numpy>=1.26"]
# ///
# pyright: reportMissingImports=false
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Iterable, TypedDict, cast

import networkx as nx

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import lib.behavioral as behavioral  # noqa: E402
import lib.cache as cache  # noqa: E402
import lib.complexity as complexity  # noqa: E402
from lib.helpers import as_int, classify  # noqa: E402
import lib.risk as risk  # noqa: E402
import lib.scanner as scanner  # noqa: E402
import lib.structural as structural  # noqa: E402
import lib.test_mapping as test_mapping  # noqa: E402

DIAGRAM_TYPES = ("dependency", "module", "risk")
NOISE_DIRS = {"__tests__", "__test__", "test", "tests"}
SKIP_DIRS = {"src", "lib", "app", "main", "python", "java", "typescript", "frontend", "backend"}
TOP_HIGHLIGHT_COUNT = 5


class RiskItem(TypedDict):
    path: str
    max_cyclomatic: int
    churn_30d: int
    risk_product: int
    has_tests: bool
    pagerank_pct: int


class AnalysisPayload(TypedDict):
    graph: nx.DiGraph
    pagerank: dict[str, float]
    communities: list[set[str]]
    risk_hotspots: list[RiskItem]


_DIAGRAM_EMITTERS = {
    "dependency": lambda data, scope, max_nodes: emit_dependency_mermaid(
        data["graph"], data["pagerank"], scope, max_nodes
    ),
    "module": lambda data, scope, max_nodes: emit_module_mermaid(
        data["graph"], data["communities"], data["pagerank"], scope, max_nodes
    ),
    "risk": lambda data, scope, max_nodes: emit_risk_mermaid(data["risk_hotspots"], scope, max_nodes),
}


def main() -> int:
    args = parse_args()
    workspace = args.workspace.resolve()
    scope = normalize_scope(args.scope)
    try:
        data = load_or_analyze(workspace)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    emitter = _DIAGRAM_EMITTERS.get(args.type)
    if emitter is None:
        print(f"Unknown diagram type: {args.type}", file=sys.stderr)
        return 1
    output = emitter(data, scope, args.max_nodes)

    if args.output is None:
        print(output)
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(output + "\n", encoding="utf-8")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Mermaid architecture diagrams from codebase-sense graph data."
    )
    parser.add_argument(
        "--workspace",
        "-w",
        type=Path,
        default=Path.cwd(),
        help="Workspace root path (default: current directory).",
    )
    parser.add_argument(
        "--type",
        "-t",
        choices=DIAGRAM_TYPES,
        default="dependency",
        help="Diagram type: dependency, module, or risk (default: dependency).",
    )
    parser.add_argument(
        "--scope",
        "-s",
        type=str,
        help="Filter to module/directory prefix.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Write diagram to file path instead of stdout.",
    )
    parser.add_argument(
        "--max-nodes",
        type=int,
        default=30,
        help="Maximum nodes to include (default: 30).",
    )
    return parser.parse_args()


def load_or_analyze(workspace: Path) -> AnalysisPayload:
    cache_fresh = cache.is_cache_fresh(workspace)
    cached = load_cached_payload(workspace) if cache_fresh else None
    if cached is not None:
        return cached

    analyzed = run_lightweight_analysis(workspace)
    persist_payload(workspace, analyzed)
    return analyzed


def load_cached_payload(workspace: Path) -> AnalysisPayload | None:
    edges_raw = cache.load_meta(workspace, "structural_graph_edges")
    pagerank_raw = cache.load_meta(workspace, "structural_pagerank")
    communities_raw = cache.load_meta(workspace, "structural_communities")
    risk_raw = cache.load_meta(workspace, "risk_hotspots")
    if not edges_raw or not pagerank_raw or not communities_raw or not risk_raw:
        return None

    try:
        edges = json.loads(edges_raw)
        pagerank = {str(k): float(v) for k, v in json.loads(pagerank_raw).items()}
        communities = [set(map(str, community)) for community in json.loads(communities_raw)]
        risk_hotspots_raw = json.loads(risk_raw)
    except (ValueError, TypeError, json.JSONDecodeError):
        return None
    if not isinstance(risk_hotspots_raw, list):
        return None

    graph = nx.DiGraph()
    graph.add_edges_from((str(src), str(dst)) for src, dst in edges)
    for node in pagerank:
        if node not in graph:
            graph.add_node(node)

    risk_hotspots: list[RiskItem] = []
    for item in risk_hotspots_raw:
        if not isinstance(item, dict):
            continue
        risk_hotspots.append(
            RiskItem(
                path=str(item.get("path", "")),
                max_cyclomatic=as_int(item.get("max_cyclomatic"), 0),
                churn_30d=as_int(item.get("churn_30d"), 0),
                risk_product=as_int(item.get("risk_product"), 0),
                has_tests=bool(item.get("has_tests", False)),
                pagerank_pct=as_int(item.get("pagerank_pct"), 0),
            )
        )

    return {
        "graph": graph,
        "pagerank": pagerank,
        "communities": communities,
        "risk_hotspots": risk_hotspots,
    }


def run_lightweight_analysis(workspace: Path) -> AnalysisPayload:
    try:
        repos = [workspace]
        files = scanner.scan_files(repos)
        graph = structural.build_dependency_graph(files)
        centrality = structural.compute_centrality(graph)
        communities = structural.detect_communities(graph)
        complexity_metrics = complexity.analyze_files(files)
        commits = behavioral.parse_git_log(workspace, since_days=30)
        commit_counts = compute_commit_counts(commits)
        tests = test_mapping.map_tests_to_sources(files)
        hotspots = risk.compute_hotspots(
            complexity=complexity_metrics,
            commit_counts=commit_counts,
            test_links=tests,
            centrality=centrality,
            top_n=200,
        )
    except Exception as exc:
        raise RuntimeError(
            "Unable to build structural graph data. Run "
            "'uv run --script .cursor/skills/codebase-sense/scripts/briefing.py "
            f"\"{workspace}\"' first. Details: {exc}"
        ) from exc

    pagerank = {path: metrics.pagerank for path, metrics in centrality.items()}
    risk_hotspots: list[RiskItem] = [
        RiskItem(
            path=hotspot.path,
            max_cyclomatic=hotspot.max_cyclomatic,
            churn_30d=hotspot.churn_30d,
            risk_product=hotspot.risk_product,
            has_tests=hotspot.has_tests,
            pagerank_pct=hotspot.pagerank_pct,
        )
        for hotspot in hotspots
    ]
    return {
        "graph": graph,
        "pagerank": pagerank,
        "communities": communities,
        "risk_hotspots": risk_hotspots,
    }


def persist_payload(workspace: Path, payload: AnalysisPayload) -> None:
    graph = payload["graph"]
    pagerank = payload["pagerank"]
    communities = payload["communities"]
    risk_hotspots = payload["risk_hotspots"]
    edges = [[str(src), str(dst)] for src, dst in graph.edges()]
    cache.save_meta(workspace, "structural_graph_edges", json.dumps(edges))
    cache.save_meta(workspace, "structural_pagerank", json.dumps(pagerank, sort_keys=True))
    cache.save_meta(
        workspace,
        "structural_communities",
        json.dumps([sorted(list(community)) for community in communities]),
    )
    cache.save_meta(workspace, "risk_hotspots", json.dumps(risk_hotspots))


def emit_dependency_mermaid(
    graph: nx.DiGraph,
    pagerank: dict[str, float],
    scope: str | None,
    max_nodes: int,
) -> str:
    module_graph, module_scores = collapse_to_modules(graph, pagerank, scope)
    selected = select_nodes_by_score(module_graph.nodes(), module_scores, max_nodes)
    trimmed = module_graph.subgraph(selected).copy()
    if not trimmed.nodes:
        return "graph TD\n    noData[\"No dependency data for selected scope\"]"

    lines = ["graph TD"]
    for module in sorted(trimmed.nodes()):
        lines.append(f"    {mermaid_id(module)}[\"{module}\"]")
    for source, target in sorted(trimmed.edges()):
        lines.append(f"    {mermaid_id(source)} --> {mermaid_id(target)}")

    top_core = sorted(selected, key=lambda name: module_scores.get(name, 0.0), reverse=True)[
        :TOP_HIGHLIGHT_COUNT
    ]
    if top_core:
        lines.append("    classDef core stroke-width:3px,font-weight:bold")
        lines.append(f"    class {','.join(mermaid_id(node) for node in top_core)} core")
    return "\n".join(lines)


def emit_module_mermaid(
    graph: nx.DiGraph,
    communities: list[set[str]],
    pagerank: dict[str, float],
    scope: str | None,
    max_nodes: int,
) -> str:
    module_graph, module_scores = collapse_to_modules(graph, pagerank, scope)
    if not module_graph.nodes():
        return "graph TD\n    noData[\"No module data for selected scope\"]"

    selected = set(select_nodes_by_score(module_graph.nodes(), module_scores, max_nodes))
    if not selected:
        return "graph TD\n    noData[\"No module data for selected scope\"]"

    module_to_community = assign_module_communities(communities)
    grouped: dict[int, list[str]] = defaultdict(list)
    for module in selected:
        grouped[module_to_community.get(module, -1)].append(module)

    lines = ["graph TD"]
    for community_id in sorted(grouped):
        modules = sorted(grouped[community_id])
        label = dominant_prefix_label(modules)
        subgraph_id = f"community{community_id if community_id >= 0 else 'x'}"
        lines.append(f"    subgraph {subgraph_id}[\"{label}\"]")
        for module in modules:
            lines.append(f"        {mermaid_id(module)}[\"{module}\"]")
        lines.append("    end")

    for source, target in sorted(module_graph.edges()):
        if source not in selected or target not in selected:
            continue
        if module_to_community.get(source, -1) == module_to_community.get(target, -1):
            continue
        lines.append(f"    {mermaid_id(source)} --> {mermaid_id(target)}")
    return "\n".join(lines)


def emit_risk_mermaid(
    risk_hotspots: list[RiskItem],
    scope: str | None,
    max_nodes: int,
) -> str:
    if not risk_hotspots:
        return "graph TD\n    noData[\"Insufficient risk data; run briefing first\"]"

    filtered = [item for item in risk_hotspots if scope_matches(item["path"], scope)]
    ranked = sorted(filtered, key=lambda item: item["risk_product"], reverse=True)[:max_nodes]
    if not ranked:
        return "graph TD\n    noData[\"No risk data for selected scope\"]"

    lines = ["graph TD"]
    class_nodes: dict[str, list[str]] = defaultdict(list)
    for item in ranked:
        path = item["path"]
        label = f"{module_from_path(path)} ({item['risk_product']})"
        node_id = mermaid_id(path)
        lines.append(f"    {node_id}[\"{label}\"]")
        class_nodes[risk_level(item["risk_product"])].append(node_id)

    lines.append("    classDef low stroke-width:1px")
    lines.append("    classDef medium stroke-width:2px,stroke-dasharray: 3 3")
    lines.append("    classDef high stroke-width:3px")
    lines.append("    classDef critical stroke-width:4px,font-weight:bold")
    for level in ("low", "medium", "high", "critical"):
        nodes = class_nodes.get(level, [])
        if nodes:
            lines.append(f"    class {','.join(nodes)} {level}")
    return "\n".join(lines)


def collapse_to_modules(
    graph: nx.DiGraph,
    pagerank: dict[str, float],
    scope: str | None,
) -> tuple[nx.DiGraph, dict[str, float]]:
    module_graph = nx.DiGraph()
    module_scores: dict[str, float] = defaultdict(float)
    for node in graph.nodes():
        if not scope_matches(str(node), scope):
            continue
        module = module_from_path(str(node))
        module_graph.add_node(module)
        module_scores[module] += float(pagerank.get(str(node), 0.0))

    for source, target in graph.edges():
        if not scope_matches(str(source), scope) and not scope_matches(str(target), scope):
            continue
        left = module_from_path(str(source))
        right = module_from_path(str(target))
        if left == right:
            continue
        module_graph.add_edge(left, right)
    return module_graph, dict(module_scores)


def assign_module_communities(communities: list[set[str]]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for index, community in enumerate(communities):
        module_counts = Counter(module_from_path(path) for path in community)
        for module in module_counts:
            current = mapping.get(module)
            if current is None:
                mapping[module] = index
    return mapping


def compute_commit_counts(commits: list[behavioral.Commit]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for commit in commits:
        for changed in {change.path for change in commit.files}:
            counts[changed] += 1
    return dict(counts)


def module_from_path(path: str) -> str:
    parts = [part for part in PurePosixPath(path.replace("\\", "/")).parts if part and part not in NOISE_DIRS]
    if len(parts) >= 2 and parts[0] not in SKIP_DIRS and parts[1] in SKIP_DIRS:
        parts = parts[1:]
    if "src" in parts:
        idx = parts.index("src")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    for part in parts[:-1]:
        if part not in SKIP_DIRS:
            return part
    if len(parts) >= 2:
        return parts[-2]
    if parts:
        return parts[0]
    return "root"


def dominant_prefix_label(modules: list[str]) -> str:
    if not modules:
        return "Community"
    prefixes = [module.split("/", 1)[0] for module in modules]
    dominant = Counter(prefixes).most_common(1)[0][0]
    return dominant.capitalize()


def select_nodes_by_score(nodes: object, scores: dict[str, float], max_nodes: int) -> list[str]:
    if max_nodes <= 0:
        return []
    ranked = sorted((str(node) for node in cast(Iterable[str], nodes)), key=lambda n: scores.get(n, 0.0), reverse=True)
    return ranked[:max_nodes]


def scope_matches(path: str, scope: str | None) -> bool:
    if scope is None:
        return True
    normalized = path.replace("\\", "/").lower()
    return normalized.startswith(scope)


def normalize_scope(scope: str | None) -> str | None:
    if not scope:
        return None
    normalized = scope.strip().replace("\\", "/").strip("/")
    if not normalized:
        return None
    return normalized.lower()


def mermaid_id(raw: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z_]", "_", raw)
    if not cleaned:
        return "node"
    if cleaned[0].isdigit():
        return f"n_{cleaned}"
    return cleaned


def risk_level(score: int) -> str:
    return classify(score, [(500, "critical"), (200, "high"), (80, "medium")], "low")


if __name__ == "__main__":
    raise SystemExit(main())
