#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = ["pyyaml>=6.0", "networkx>=3.0"]
# ///
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import networkx as nx  # type: ignore[import-untyped]
import yaml  # type: ignore[import-untyped]

LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
SEE_RE = re.compile(r"\bsee\s+([a-z0-9][a-z0-9-]*)(?:\s+skill)?\b", re.IGNORECASE)


@dataclass(frozen=True)
class Node:
    node_id: str
    kind: str
    path: Path


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    edge_type: str


def _detect_cursor_dir(explicit: Path | None) -> Path | None:
    if explicit is not None:
        return explicit.resolve()
    current = Path.cwd().resolve()
    for candidate in [current, *current.parents]:
        maybe = candidate / ".cursor"
        if maybe.is_dir():
            return maybe
    return None


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    frontmatter = yaml.safe_load(parts[1]) or {}
    body = parts[2]
    return frontmatter if isinstance(frontmatter, dict) else {}, body


def _collect_nodes(cursor_dir: Path, include_rules: bool) -> dict[str, Node]:
    nodes: dict[str, Node] = {}
    skills_dir = cursor_dir / "skills"
    if skills_dir.is_dir():
        for skill_dir in sorted(skills_dir.iterdir()):
            skill_file = skill_dir / "SKILL.md"
            if not skill_dir.is_dir() or not skill_file.is_file():
                continue
            nodes[skill_dir.name] = Node(node_id=skill_dir.name, kind="skill", path=skill_file)
    if not include_rules:
        return nodes
    rules_dir = cursor_dir / "rules"
    if not rules_dir.is_dir():
        return nodes
    for rule_dir in sorted(rules_dir.iterdir()):
        rule_file = rule_dir / "RULE.mdc"
        if not rule_dir.is_dir() or not rule_file.is_file():
            continue
        if rule_dir.name in nodes:
            nodes[f"rule-{rule_dir.name}"] = Node(
                node_id=f"rule-{rule_dir.name}",
                kind="rule",
                path=rule_file,
            )
            continue
        nodes[rule_dir.name] = Node(node_id=rule_dir.name, kind="rule", path=rule_file)
    return nodes


def _extract_target_from_link(link: str, known_ids: set[str]) -> str | None:
    clean = link.split("#", 1)[0].split("?", 1)[0].strip()
    if not clean:
        return None
    posix = PurePosixPath(clean.replace("\\", "/"))
    parts = [part for part in posix.parts if part not in {".", ".."}]
    if not parts:
        return None
    if "skills" in parts:
        idx = parts.index("skills")
        if idx + 1 < len(parts) and parts[idx + 1] in known_ids:
            return parts[idx + 1]
    if "rules" in parts:
        idx = parts.index("rules")
        if idx + 1 < len(parts) and parts[idx + 1] in known_ids:
            return parts[idx + 1]
    if parts[-1].lower() in {"skill.md", "rule.mdc"} and len(parts) >= 2:
        candidate = parts[-2]
        if candidate in known_ids:
            return candidate
    return None


def _detect_references(source: str, text: str, known_ids: set[str]) -> set[Edge]:
    edges: set[Edge] = set()
    for line in text.splitlines():
        lower = line.lower()
        for match in LINK_RE.finditer(line):
            target = _extract_target_from_link(match.group(1), known_ids)
            if target and target != source:
                edges.add(Edge(source=source, target=target, edge_type="resource"))
        for match in SEE_RE.finditer(line):
            candidate = match.group(1).lower()
            if candidate not in known_ids or candidate == source:
                continue
            edge_type = "boundary" if "do not use" in lower else "see"
            edges.add(Edge(source=source, target=candidate, edge_type=edge_type))
    existing_pairs = {(edge.source, edge.target) for edge in edges}
    for target in known_ids:
        if target == source:
            continue
        token = re.escape(target)
        if not re.search(rf"(?<![a-z0-9-]){token}(?![a-z0-9-])", text, re.IGNORECASE):
            continue
        if (source, target) in existing_pairs:
            continue
        edges.add(Edge(source=source, target=target, edge_type="mention"))
    return edges


def _collect_edges(nodes: dict[str, Node]) -> list[Edge]:
    known_ids = set(nodes.keys())
    all_edges: set[Edge] = set()
    for source_id, node in nodes.items():
        text = _read_text(node.path)
        fm, body = _parse_frontmatter(text)
        description = fm.get("description", "") if isinstance(fm, dict) else ""
        haystack = f"{description}\n{body}".strip()
        if not haystack:
            continue
        all_edges.update(_detect_references(source_id, haystack, known_ids))
    return sorted(all_edges, key=lambda edge: (edge.source, edge.target, edge.edge_type))


def _build_graph(nodes: dict[str, Node], edges: list[Edge]) -> nx.DiGraph:
    graph = nx.DiGraph()
    for node in nodes.values():
        graph.add_node(node.node_id, kind=node.kind, path=str(node.path))
    for edge in edges:
        graph.add_edge(edge.source, edge.target)
    return graph


def _compute_clusters(graph: nx.DiGraph) -> list[list[str]]:
    if graph.number_of_nodes() == 0:
        return []
    components = nx.connected_components(graph.to_undirected())
    clusters = [sorted(component) for component in components]
    return sorted(clusters, key=lambda cluster: (-len(cluster), cluster[0]))


def _compute_orphans(graph: nx.DiGraph) -> list[str]:
    return sorted(
        node
        for node in graph.nodes()
        if graph.in_degree(node) == 0 and graph.out_degree(node) == 0
    )


def _compute_missing_edges(graph: nx.DiGraph, clusters: list[list[str]]) -> list[tuple[str, str]]:
    missing: list[tuple[str, str]] = []
    for cluster in clusters:
        if len(cluster) < 2:
            continue
        for idx, source in enumerate(cluster):
            for target in cluster[idx + 1 :]:
                if graph.has_edge(source, target) or graph.has_edge(target, source):
                    continue
                missing.append((source, target))
    return missing


def _compute_reciprocity(graph: nx.DiGraph) -> tuple[int, int]:
    seen_pairs: set[tuple[str, str]] = set()
    bidirectional = 0
    oneway = 0
    for source, target in graph.edges():
        if source == target:
            continue
        ordered = tuple(sorted((source, target)))
        if ordered in seen_pairs:
            continue
        seen_pairs.add(ordered)
        if graph.has_edge(target, source):
            bidirectional += 1
        else:
            oneway += 1
    return bidirectional, oneway


def _camel_case(value: str) -> str:
    parts = [part for part in re.split(r"[^a-zA-Z0-9]+", value) if part]
    if not parts:
        return "node"
    head = parts[0].lower()
    tail = "".join(part[:1].upper() + part[1:] for part in parts[1:])
    camel = f"{head}{tail}"
    if camel[0].isdigit():
        return f"n{camel}"
    return camel


def _format_text(
    graph: nx.DiGraph,
    clusters: list[list[str]],
    orphans: list[str],
    missing_edges: list[tuple[str, str]],
) -> str:
    incoming_counts = {node: len(graph.pred.get(node, {})) for node in graph.nodes()}
    outgoing_counts = {node: len(graph.succ.get(node, {})) for node in graph.nodes()}
    top_incoming = sorted(graph.nodes(), key=lambda node: (-incoming_counts.get(node, 0), node))[:10]
    top_outgoing = sorted(graph.nodes(), key=lambda node: (-outgoing_counts.get(node, 0), node))[:10]
    bidirectional, oneway = _compute_reciprocity(graph)

    lines = [
        "Knowledge Graph Analysis",
        "========================",
        f"Skills scanned: {graph.number_of_nodes()}",
        f"Edges detected: {graph.number_of_edges()}",
        "",
        "Knowledge Hubs (most referenced):",
    ]
    if not top_incoming:
        lines.append("  (none)")
    else:
        for idx, node in enumerate(top_incoming, start=1):
            lines.append(f"  {idx}. {node} ({incoming_counts.get(node, 0)} incoming refs)")
    lines.extend(["", "Integration Points (most outgoing refs):"])
    if not top_outgoing:
        lines.append("  (none)")
    else:
        for idx, node in enumerate(top_outgoing, start=1):
            lines.append(f"  {idx}. {node} ({outgoing_counts.get(node, 0)} outgoing refs)")
    lines.extend(["", "Orphan Skills (no connections):"])
    if not orphans:
        lines.append("  (none)")
    else:
        for orphan in orphans:
            lines.append(f"  - {orphan}")
    lines.extend(["", "Clusters:"])
    if not clusters:
        lines.append("  (none)")
    else:
        for idx, cluster in enumerate(clusters, start=1):
            lines.append(f"  Cluster {idx}: [{', '.join(cluster)}]")
    lines.extend(["", "Potential Missing Edges:"])
    if not missing_edges:
        lines.append("  (none)")
    else:
        for source, target in missing_edges[:20]:
            lines.append(
                f"  - {source} and {target} are in the same cluster but don't reference each other"
            )
        if len(missing_edges) > 20:
            lines.append(f"  ... {len(missing_edges) - 20} more")
    lines.extend(
        [
            "",
            "Reciprocity:",
            f"  - Bidirectional pairs: {bidirectional}",
            f"  - One-way pairs: {oneway}",
        ]
    )
    return "\n".join(lines)


def _format_mermaid(graph: nx.DiGraph, clusters: list[list[str]]) -> str:
    lines = ["graph LR"]
    node_ids: dict[str, str] = {}
    used_ids: set[str] = set()
    for node in sorted(graph.nodes()):
        candidate = _camel_case(node)
        while candidate in used_ids:
            candidate = f"{candidate}X"
        used_ids.add(candidate)
        node_ids[node] = candidate
    for idx, cluster in enumerate(clusters, start=1):
        lines.append(f'    subgraph cluster{idx} ["Cluster {idx}"]')
        for node in cluster:
            lines.append(f'        {node_ids[node]}["{node}"]')
        lines.append("    end")
    for source, target in sorted(graph.edges()):
        lines.append(f"    {node_ids[source]} --> {node_ids[target]}")
    return "\n".join(lines)


def _format_json(
    graph: nx.DiGraph,
    edges: list[Edge],
    clusters: list[list[str]],
    orphans: list[str],
) -> str:
    cluster_map: dict[str, int] = {}
    for idx, cluster in enumerate(clusters):
        for node in cluster:
            cluster_map[node] = idx
    payload = {
        "nodes": [
            {
                "id": node,
                "in_degree": graph.in_degree(node),
                "out_degree": graph.out_degree(node),
                "cluster": cluster_map.get(node, -1),
            }
            for node in sorted(graph.nodes())
        ],
        "edges": [
            {"source": edge.source, "target": edge.target, "type": edge.edge_type}
            for edge in edges
        ],
        "orphans": orphans,
        "clusters": clusters,
    }
    return json.dumps(payload, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a cross-reference graph for .cursor skills and rules."
    )
    parser.add_argument(
        "-d",
        "--cursor-dir",
        type=Path,
        default=None,
        help="Path to .cursor directory (default: auto-detect from cwd upward).",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["text", "mermaid", "json"],
        default="text",
        help="Output format.",
    )
    parser.add_argument(
        "--include-rules",
        action="store_true",
        help="Include .cursor/rules/*/RULE.mdc nodes in the graph.",
    )
    args = parser.parse_args()

    cursor_dir = _detect_cursor_dir(args.cursor_dir)
    if cursor_dir is None:
        print(
            "Error: Could not find a .cursor directory. Pass --cursor-dir explicitly.",
            file=sys.stderr,
        )
        return 1
    if not cursor_dir.is_dir():
        print(f"Error: {cursor_dir} is not a directory.", file=sys.stderr)
        return 1

    nodes = _collect_nodes(cursor_dir, args.include_rules)
    if not nodes:
        print("No skills found to analyze.", file=sys.stderr)
        return 1

    edges = _collect_edges(nodes)
    graph = _build_graph(nodes, edges)
    clusters = _compute_clusters(graph)
    orphans = _compute_orphans(graph)
    missing_edges = _compute_missing_edges(graph, clusters)

    if args.format == "text":
        print(_format_text(graph, clusters, orphans, missing_edges))
        return 0
    if args.format == "mermaid":
        print(_format_mermaid(graph, clusters))
        return 0
    print(_format_json(graph, edges, clusters, orphans))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
