# pyright: reportMissingImports=false
from __future__ import annotations

import re
import tomllib
from collections import Counter, namedtuple
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

import networkx as nx
import numpy as np

from .scanner import SourceFile

CentralityMetrics = namedtuple(
    "CentralityMetrics",
    ["pagerank", "authority", "hub", "betweenness", "classification"],
)
DriftFile = namedtuple("DriftFile", ["path", "community_id", "expected_dir"])

_TS_IMPORT_RE = re.compile(
    r"^\s*import\s+(?:.+?\s+from\s+)?[\"']([^\"']+)[\"']",
    flags=re.MULTILINE,
)
_JAVA_IMPORT_RE = re.compile(r"^\s*import\s+([a-zA-Z0-9_.]+);", flags=re.MULTILINE)
_PY_FROM_IMPORT_RE = re.compile(
    r"^\s*from\s+([a-zA-Z0-9_.]+)\s+import\b",
    flags=re.MULTILINE,
)
_PY_IMPORT_RE = re.compile(
    r"^\s*import\s+([a-zA-Z0-9_.,\s]+)",
    flags=re.MULTILINE,
)
_RUST_USE_RE = re.compile(r"^\s*(?:pub\s+)?use\s+(.+?)\s*;", flags=re.MULTILINE | re.DOTALL)
_RUST_MOD_RE = re.compile(
    r"^\s*(?:pub(?:\(crate\))?\s+)?mod\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*;",
    flags=re.MULTILINE,
)


@dataclass
class WorkspaceContext:
    cargo_crates: dict[str, str] = field(default_factory=dict)
    repo_roots: dict[str, Path] = field(default_factory=dict)


ImportParser = Callable[[SourceFile, str, dict[str, SourceFile], WorkspaceContext], list[str]]


def _parse_ts_imports(
    source_file: SourceFile,
    content: str,
    all_files: dict[str, SourceFile],
    _context: WorkspaceContext,
) -> list[str]:
    imports: set[str] = set()
    for match in _TS_IMPORT_RE.findall(content):
        if match.startswith("./") or match.startswith("../"):
            resolved = _resolve_ts_import(source_file.path, match, all_files)
            if resolved:
                imports.add(resolved)
    return sorted(imports)


def _parse_py_imports(
    source_file: SourceFile,
    content: str,
    all_files: dict[str, SourceFile],
    _context: WorkspaceContext,
) -> list[str]:
    imports: set[str] = set()
    for match in _PY_FROM_IMPORT_RE.findall(content):
        if match.startswith("."):
            resolved = _resolve_py_relative_import(source_file.path, match, all_files)
        else:
            resolved = _resolve_py_absolute_import(
                source_file.path, source_file.repo, match, all_files
            )
        if resolved:
            imports.add(resolved)
    for match in _PY_IMPORT_RE.findall(content):
        for module in (part.strip() for part in match.split(",")):
            if not module:
                continue
            resolved = _resolve_py_absolute_import(
                source_file.path, source_file.repo, module, all_files
            )
            if resolved:
                imports.add(resolved)
    return sorted(imports)


def _parse_svelte_imports(
    source_file: SourceFile,
    content: str,
    all_files: dict[str, SourceFile],
    _context: WorkspaceContext,
) -> list[str]:
    imports: set[str] = set()
    for match in _TS_IMPORT_RE.findall(content):
        if match.startswith("./") or match.startswith("../"):
            resolved = _resolve_svelte_import(source_file.path, match, all_files)
            if resolved:
                imports.add(resolved)
    return sorted(imports)


def _parse_java_imports(
    source_file: SourceFile,
    content: str,
    all_files: dict[str, SourceFile],
    context: WorkspaceContext,
) -> list[str]:
    imports: set[str] = set()
    repo_root = context.repo_roots.get(source_file.repo) or _find_repo_root(
        source_file.abs_path, source_file.repo
    )
    if repo_root is None:
        return []
    for package in _JAVA_IMPORT_RE.findall(content):
        if package.endswith(".*"):
            continue

        package_path = PurePosixPath(*package.split("."))
        candidate = (
            PurePosixPath(source_file.repo) / "src" / "main" / "java" / package_path
        ).with_suffix(".java")
        candidate_key = candidate.as_posix()
        if candidate_key in all_files:
            imports.add(candidate_key)
            continue

        absolute_candidate = repo_root / "src" / "main" / "java" / Path(*package.split("."))
        absolute_candidate = absolute_candidate.with_suffix(".java")
        if absolute_candidate.exists():
            resolved = _to_source_key(absolute_candidate, repo_root.parent)
            if resolved in all_files:
                imports.add(resolved)
    return sorted(imports)


def _parse_rust_imports(
    source_file: SourceFile,
    content: str,
    all_files: dict[str, SourceFile],
    context: WorkspaceContext,
) -> list[str]:
    imports: set[str] = set()
    for clause in _RUST_USE_RE.findall(content):
        for expanded in _expand_rust_use_clause(clause):
            resolved = _resolve_rust_use(source_file, expanded, all_files, context)
            if resolved:
                imports.add(resolved)
    for module_name in _RUST_MOD_RE.findall(content):
        resolved = _resolve_rust_mod(source_file, module_name, all_files)
        if resolved:
            imports.add(resolved)
    return sorted(imports)


_IMPORT_PARSERS: dict[str, ImportParser] = {
    "typescript": _parse_ts_imports,
    "python": _parse_py_imports,
    "svelte": _parse_svelte_imports,
    "java": _parse_java_imports,
    "rust": _parse_rust_imports,
}


def parse_imports(
    source_file: SourceFile,
    all_files: dict[str, SourceFile],
    context: WorkspaceContext | None = None,
) -> list[str]:
    parser_fn = _IMPORT_PARSERS.get(source_file.language)
    if parser_fn is None:
        return []

    try:
        content = source_file.abs_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []

    return parser_fn(source_file, content, all_files, context or WorkspaceContext())


def build_dependency_graph(files: list[SourceFile]) -> nx.DiGraph:
    graph = nx.DiGraph()
    all_files = {source_file.path: source_file for source_file in files}
    context = _build_workspace_context(files)

    for source_file in files:
        graph.add_node(
            source_file.path,
            loc=source_file.loc,
            language=source_file.language,
            repo=source_file.repo,
        )

    for source_file in files:
        for dependency in parse_imports(source_file, all_files, context=context):
            if dependency in all_files:
                graph.add_edge(source_file.path, dependency)

    return graph


def compute_centrality(graph: nx.DiGraph) -> dict[str, CentralityMetrics]:
    if graph.number_of_nodes() == 0:
        return {}

    pagerank = _compute_pagerank(graph)
    betweenness = nx.betweenness_centrality(graph)

    try:
        hubs, authorities = _compute_hits_numpy(graph)
    except Exception:
        hubs = {node: 0.0 for node in graph.nodes}
        authorities = {node: 0.0 for node in graph.nodes}

    metrics: dict[str, CentralityMetrics] = {}
    for node in graph.nodes:
        authority = float(authorities.get(node, 0.0))
        hub = float(hubs.get(node, 0.0))
        metrics[node] = CentralityMetrics(
            pagerank=float(pagerank.get(node, 0.0)),
            authority=authority,
            hub=hub,
            betweenness=float(betweenness.get(node, 0.0)),
            classification="authority" if authority > hub else "bridge",
        )

    return metrics


def detect_communities(graph: nx.DiGraph) -> list[set[str]]:
    if graph.number_of_nodes() == 0:
        return []

    undirected = graph.to_undirected()
    connected = [n for n in undirected.nodes() if undirected.degree(n) > 0]
    if not connected:
        return []

    subgraph = undirected.subgraph(connected)

    try:
        return [set(c) for c in nx.community.louvain_communities(subgraph, resolution=1.0, seed=42)]
    except Exception:
        return [set(c) for c in nx.connected_components(subgraph)]


def compute_boundary_alignment(communities: list[set[str]]) -> tuple[float, list[DriftFile]]:
    total_files = sum(len(community) for community in communities)
    if total_files == 0:
        return 100.0, []

    matching = 0
    drift_files: list[DriftFile] = []

    for community_id, community in enumerate(communities, start=1):
        directory_groups = [_directory_prefix(path) for path in community]
        dominant_dir = Counter(directory_groups).most_common(1)[0][0]

        for path in sorted(community):
            current_dir = _directory_prefix(path)
            if current_dir == dominant_dir:
                matching += 1
            else:
                drift_files.append(
                    DriftFile(path=path, community_id=community_id, expected_dir=dominant_dir)
                )

    alignment = (matching / total_files) * 100.0
    return alignment, drift_files


def _resolve_ts_import(
    source_path: str, import_path: str, all_files: dict[str, SourceFile]
) -> str | None:
    source_dir = PurePosixPath(source_path).parent
    base = _normalize_posix((source_dir / import_path).as_posix())

    candidates = [base, f"{base}.ts", f"{base}/index.ts"]
    for candidate in candidates:
        normalized = _normalize_posix(candidate)
        if normalized in all_files:
            return normalized
    return None


def _resolve_py_relative_import(
    source_path: str, import_spec: str, all_files: dict[str, SourceFile]
) -> str | None:
    source_dir = PurePosixPath(source_path).parent
    dots = len(import_spec) - len(import_spec.lstrip("."))
    module_part = import_spec.lstrip(".")

    base = source_dir
    for _ in range(dots - 1):
        base = base.parent

    if module_part:
        module_path = base / module_part.replace(".", "/")
    else:
        module_path = base

    candidates = [
        f"{module_path}.py",
        f"{module_path}/__init__.py",
    ]
    for candidate in candidates:
        normalized = _normalize_posix(candidate)
        if normalized in all_files:
            return normalized
    return None


def _resolve_py_absolute_import(
    source_path: str, repo_name: str, import_spec: str, all_files: dict[str, SourceFile]
) -> str | None:
    parts = import_spec.split(".")
    normalized_source = source_path.replace("\\", "/")
    base_paths: list[PurePosixPath] = []
    if "/src/" in normalized_source:
        source_root = normalized_source.split("/src/", 1)[0]
        base_paths.append(PurePosixPath(source_root) / "src")
        base_paths.append(PurePosixPath(source_root))
    base_paths.append(PurePosixPath(repo_name) / "src")
    base_paths.append(PurePosixPath(repo_name))

    seen_bases: set[str] = set()
    for base_path in base_paths:
        base_key = _normalize_posix(base_path.as_posix())
        if base_key in seen_bases:
            continue
        seen_bases.add(base_key)

        module_path = PurePosixPath(base_key) / "/".join(parts)
        candidates = [
            f"{module_path}.py",
            f"{module_path}/__init__.py",
        ]
        for candidate in candidates:
            normalized = _normalize_posix(candidate)
            if normalized in all_files:
                return normalized
    return None


def _resolve_svelte_import(
    source_path: str, import_path: str, all_files: dict[str, SourceFile]
) -> str | None:
    source_dir = PurePosixPath(source_path).parent
    base = _normalize_posix((source_dir / import_path).as_posix())
    candidates = [base, f"{base}.ts", f"{base}.svelte", f"{base}/index.ts"]
    for candidate in candidates:
        normalized = _normalize_posix(candidate)
        if normalized in all_files:
            return normalized
    return None


def _build_workspace_context(files: list[SourceFile]) -> WorkspaceContext:
    context = WorkspaceContext()
    if not files:
        return context

    for source_file in files:
        if source_file.repo in context.repo_roots:
            continue
        repo_root = _find_repo_root(source_file.abs_path, source_file.repo)
        if repo_root is not None:
            context.repo_roots[source_file.repo] = repo_root

    for repo_name, repo_root in context.repo_roots.items():
        _register_repo_cargo_crates(repo_name, repo_root, context)

    return context


def _register_repo_cargo_crates(repo_name: str, repo_root: Path, context: WorkspaceContext) -> None:
    cargo_toml = repo_root / "Cargo.toml"
    if not cargo_toml.exists():
        return

    cargo_data = _read_toml(cargo_toml)
    if not cargo_data:
        return

    package = cargo_data.get("package")
    if isinstance(package, dict):
        package_name = package.get("name")
        if isinstance(package_name, str):
            context.cargo_crates[package_name] = ""

    workspace = cargo_data.get("workspace")
    if not isinstance(workspace, dict):
        return

    members = workspace.get("members")
    if not isinstance(members, list):
        return

    for member in members:
        if not isinstance(member, str):
            continue
        member_matches = list(repo_root.glob(member))
        if not member_matches:
            member_matches = [repo_root / member]
        for member_path in member_matches:
            if not member_path.is_dir():
                continue
            member_cargo = member_path / "Cargo.toml"
            if not member_cargo.exists():
                continue
            member_data = _read_toml(member_cargo)
            if not member_data:
                continue
            member_package = member_data.get("package")
            if not isinstance(member_package, dict):
                continue
            crate_name = member_package.get("name")
            if not isinstance(crate_name, str):
                continue
            rel_prefix = member_path.resolve().relative_to(repo_root.resolve()).as_posix()
            context.cargo_crates[crate_name] = _normalize_posix(rel_prefix)


def _read_toml(path: Path) -> dict[str, object] | None:
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _expand_rust_use_clause(clause: str) -> list[str]:
    cleaned = clause.strip()
    if "{" not in cleaned or "}" not in cleaned:
        return [cleaned]

    brace_open = cleaned.find("{")
    brace_close = cleaned.rfind("}")
    if brace_open < 0 or brace_close <= brace_open:
        return [cleaned]

    prefix = cleaned[:brace_open].rstrip(":")
    inner = cleaned[brace_open + 1 : brace_close]
    parts = [part.strip() for part in inner.split(",") if part.strip()]
    if not parts:
        return [cleaned]

    if not prefix:
        return parts
    return [f"{prefix}::{part}" for part in parts]


def _resolve_rust_use(
    source_file: SourceFile,
    use_path: str,
    all_files: dict[str, SourceFile],
    context: WorkspaceContext,
) -> str | None:
    segments = [segment.strip() for segment in use_path.split("::") if segment.strip()]
    if not segments:
        return None

    if " as " in segments[-1]:
        segments[-1] = segments[-1].split(" as ", 1)[0].strip()

    repo_relative = _repo_relative_path(source_file.path, source_file.repo)
    current_dir = PurePosixPath(repo_relative).parent

    current_crate_prefix = _current_crate_prefix(source_file, context)
    if segments[0] == "crate":
        return _resolve_rust_in_crate(source_file.repo, current_crate_prefix, segments[1:], all_files)
    if segments[0] in {"self", "super"}:
        return _resolve_rust_relative(source_file.repo, current_dir, segments, all_files)

    crate_candidates = [segments[0], segments[0].replace("_", "-")]
    for crate_name in crate_candidates:
        crate_prefix = context.cargo_crates.get(crate_name)
        if crate_prefix is None:
            continue
        resolved = _resolve_rust_in_crate(
            source_file.repo,
            crate_prefix,
            segments[1:],
            all_files,
        )
        if resolved:
            return resolved
    return None


def _current_crate_prefix(source_file: SourceFile, context: WorkspaceContext) -> str:
    repo_root = context.repo_roots.get(source_file.repo)
    if repo_root is None:
        repo_root = _find_repo_root(source_file.abs_path, source_file.repo)
    if repo_root is None:
        return ""

    crate_root = _find_crate_root(source_file.abs_path)
    if crate_root is None:
        return ""

    try:
        return _normalize_posix(crate_root.resolve().relative_to(repo_root.resolve()).as_posix())
    except ValueError:
        return ""


def _resolve_rust_relative(
    repo_name: str,
    current_dir: PurePosixPath,
    segments: list[str],
    all_files: dict[str, SourceFile],
) -> str | None:
    base_dir = PurePosixPath(repo_name) / current_dir
    index = 0
    while index < len(segments) and segments[index] in {"self", "super"}:
        token = segments[index]
        if token == "super":
            base_dir = base_dir.parent
        index += 1
    remaining = segments[index:]
    return _resolve_rust_module_candidates(repo_name, base_dir, remaining, all_files)


def _resolve_rust_in_crate(
    repo_name: str,
    crate_prefix: str,
    segments: list[str],
    all_files: dict[str, SourceFile],
) -> str | None:
    crate_root = PurePosixPath(repo_name)
    if crate_prefix:
        crate_root = crate_root / crate_prefix
    src_dir = crate_root / "src"
    return _resolve_rust_module_candidates(repo_name, src_dir, segments, all_files)


def _resolve_rust_module_candidates(
    repo_name: str,
    base_dir: PurePosixPath,
    segments: list[str],
    all_files: dict[str, SourceFile],
) -> str | None:
    if not segments:
        return None

    cleaned_segments = [segment.split(" as ", 1)[0].strip() for segment in segments if segment]
    if not cleaned_segments:
        return None

    for end in range(len(cleaned_segments), 0, -1):
        module_path = base_dir / "/".join(cleaned_segments[:end])
        candidates = [f"{module_path}.rs", f"{module_path}/mod.rs"]
        for candidate in candidates:
            normalized = _normalize_posix(candidate)
            if normalized in all_files:
                return normalized

    if str(base_dir).startswith(repo_name):
        base_candidates = [
            f"{base_dir}.rs",
            f"{base_dir}/mod.rs",
            f"{base_dir}/lib.rs",
            f"{base_dir}/main.rs",
        ]
        for candidate in base_candidates:
            normalized = _normalize_posix(candidate)
            if normalized in all_files:
                return normalized
    return None


def _resolve_rust_mod(
    source_file: SourceFile, module_name: str, all_files: dict[str, SourceFile]
) -> str | None:
    repo_relative = _repo_relative_path(source_file.path, source_file.repo)
    source_dir = PurePosixPath(repo_relative).parent
    module_base = source_dir / module_name
    candidates = [f"{module_base}.rs", f"{module_base}/mod.rs"]
    for candidate in candidates:
        normalized = _normalize_posix(f"{source_file.repo}/{candidate}")
        if normalized in all_files:
            return normalized
    return None


def _repo_relative_path(path: str, repo_name: str) -> str:
    normalized = _normalize_posix(path)
    prefix = f"{repo_name}/"
    if normalized.startswith(prefix):
        return normalized[len(prefix) :]
    return normalized


def _normalize_posix(raw_path: str) -> str:
    normalized_parts: list[str] = []
    for part in raw_path.replace("\\", "/").split("/"):
        if part in {"", "."}:
            continue
        if part == "..":
            if normalized_parts:
                normalized_parts.pop()
            continue
        normalized_parts.append(part)
    return "/".join(normalized_parts)


def _find_repo_root(abs_path: Path, repo_name: str) -> Path | None:
    current = abs_path
    while current.parent != current:
        if current.name == repo_name:
            return current
        current = current.parent
    return None


def _find_crate_root(abs_path: Path) -> Path | None:
    current = abs_path if abs_path.is_dir() else abs_path.parent
    while current.parent != current:
        if (current / "Cargo.toml").exists():
            return current
        current = current.parent
    return None


def _to_source_key(file_path: Path, common_parent: Path) -> str:
    return file_path.resolve().relative_to(common_parent.resolve()).as_posix()


def _directory_prefix(path: str) -> str:
    parts = list(PurePosixPath(path).parts[:-1])
    parts = [p for p in parts if p not in {"__tests__", "tests", "__test__", "test"}]
    if not parts:
        return ""
    max_depth = min(len(parts), 8)
    return "/".join(parts[:max_depth])


def _compute_hits_numpy(graph: nx.DiGraph) -> tuple[dict[str, float], dict[str, float]]:
    nodes = list(graph.nodes())
    if not nodes:
        return {}, {}

    adjacency = nx.to_numpy_array(graph, nodelist=nodes, dtype=np.dtype(np.float64))
    if adjacency.size == 0:
        return ({node: 0.0 for node in nodes}, {node: 0.0 for node in nodes})

    n = len(nodes)
    hubs = np.ones(n, dtype=float) / n
    authorities = np.ones(n, dtype=float) / n

    for _ in range(100):
        authorities = adjacency.T @ hubs
        auth_norm = np.linalg.norm(authorities)
        if auth_norm > 0:
            authorities = authorities / auth_norm

        hubs = adjacency @ authorities
        hub_norm = np.linalg.norm(hubs)
        if hub_norm > 0:
            hubs = hubs / hub_norm

    hub_scores = {node: float(hubs[index]) for index, node in enumerate(nodes)}
    authority_scores = {node: float(authorities[index]) for index, node in enumerate(nodes)}
    return hub_scores, authority_scores


def _compute_pagerank(
    graph: nx.DiGraph, damping: float = 0.85, max_iter: int = 100, tolerance: float = 1.0e-6
) -> dict[str, float]:
    nodes = list(graph.nodes())
    if not nodes:
        return {}

    n = len(nodes)
    index = {node: i for i, node in enumerate(nodes)}
    rank = np.ones(n, dtype=float) / n
    out_degree = np.array([graph.out_degree(node) for node in nodes], dtype=float)

    for _ in range(max_iter):
        next_rank = np.full(n, (1.0 - damping) / n, dtype=float)

        dangling_mass = rank[out_degree == 0.0].sum()
        if dangling_mass > 0:
            next_rank += damping * dangling_mass / n

        for source_idx, source in enumerate(nodes):
            degree = out_degree[source_idx]
            if degree <= 0:
                continue
            contribution = damping * rank[source_idx] / degree
            for target in graph.successors(source):
                next_rank[index[target]] += contribution

        if np.abs(next_rank - rank).sum() <= tolerance:
            rank = next_rank
            break
        rank = next_rank

    total = rank.sum()
    if total > 0:
        rank = rank / total

    return {node: float(rank[idx]) for idx, node in enumerate(nodes)}
