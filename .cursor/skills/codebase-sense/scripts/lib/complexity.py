# pyright: reportMissingImports=false
from __future__ import annotations

import re
from dataclasses import dataclass
from collections.abc import Callable
from pathlib import Path
from typing import Any, NamedTuple

from .scanner import SourceFile

try:
    import tree_sitter_python as ts_python
    import tree_sitter_rust as ts_rust
    import tree_sitter_typescript as ts_typescript
    from tree_sitter import Language, Parser
except Exception:
    Language = None  # type: ignore[assignment]
    Parser = None  # type: ignore[assignment]
    ts_python = None  # type: ignore[assignment]
    ts_rust = None  # type: ignore[assignment]
    ts_typescript = None  # type: ignore[assignment]


class ComplexityMetrics(NamedTuple):
    path: str
    language: str
    function_count: int
    max_cyclomatic: int
    avg_cyclomatic: float
    max_nesting: int
    parser_source: str
    parse_ok: bool


@dataclass(frozen=True)
class LanguageProfile:
    name: str
    parser: Any
    function_nodes: frozenset[str]
    branch_nodes: frozenset[str]
    scope_nodes: frozenset[str]
    branch_counter: Callable[[Any, bytes], int]
    heuristic_fn_patterns: tuple[str, ...]
    heuristic_branch_patterns: tuple[str, ...]
    heuristic_nesting_fn: Callable[[str], int]

_TS_FUNCTION_NODES = {"function_declaration", "method_definition", "arrow_function"}
_TS_BRANCH_NODES = {
    "if_statement",
    "for_statement",
    "for_in_statement",
    "while_statement",
    "do_statement",
    "switch_case",
    "catch_clause",
    "ternary_expression",
}
_TS_SCOPE_NODES = {
    "statement_block",
    "if_statement",
    "else_clause",
    "for_statement",
    "for_in_statement",
    "while_statement",
    "do_statement",
    "switch_statement",
    "switch_case",
    "try_statement",
    "catch_clause",
}

_PY_FUNCTION_NODES = {"function_definition"}
_PY_BRANCH_NODES = {
    "if_statement",
    "elif_clause",
    "for_statement",
    "while_statement",
    "except_clause",
    "conditional_expression",
    "boolean_operator",
}
_PY_SCOPE_NODES = {
    "block",
    "if_statement",
    "elif_clause",
    "else_clause",
    "for_statement",
    "while_statement",
    "try_statement",
    "except_clause",
    "with_statement",
}

_RUST_FUNCTION_NODES = {"function_item", "closure_expression"}
_RUST_BRANCH_NODES = {
    "if_expression",
    "match_arm",
    "for_expression",
    "while_expression",
    "loop_expression",
    "else_clause",
}
_RUST_SCOPE_NODES = {
    "block",
    "if_expression",
    "else_clause",
    "for_expression",
    "while_expression",
    "loop_expression",
    "match_expression",
    "match_arm",
    "unsafe_block",
}


def _build_parser(language_constructor: Callable[[], object] | None) -> Any:
    if Language is None or Parser is None or language_constructor is None:
        return None
    try:
        return Parser(Language(language_constructor()))
    except Exception:
        return None


_PROFILES: dict[str, LanguageProfile] = {}

_PROFILES["typescript"] = LanguageProfile(
    name="typescript",
    parser=_build_parser(
        ts_typescript.language_typescript if ts_typescript is not None else None
    ),
    function_nodes=frozenset(_TS_FUNCTION_NODES),
    branch_nodes=frozenset(_TS_BRANCH_NODES),
    scope_nodes=frozenset(_TS_SCOPE_NODES),
    branch_counter=lambda node, source_bytes: _ts_branch_increment(node, source_bytes),
    heuristic_fn_patterns=(
        r"\bfunction\b",
        r"=>",
        r"^\s*[A-Za-z_$][A-Za-z0-9_$]*\s*\([^)]*\)\s*\{",
    ),
    heuristic_branch_patterns=(
        r"\bif\b",
        r"\bfor\b",
        r"\bwhile\b",
        r"\bcase\b",
        r"\bcatch\b",
        r"\?",
        r"&&",
        r"\|\|",
    ),
    heuristic_nesting_fn=lambda source: _heuristic_ts_nesting(source),
)

_PROFILES["python"] = LanguageProfile(
    name="python",
    parser=_build_parser(ts_python.language if ts_python is not None else None),
    function_nodes=frozenset(_PY_FUNCTION_NODES),
    branch_nodes=frozenset(_PY_BRANCH_NODES),
    scope_nodes=frozenset(_PY_SCOPE_NODES),
    branch_counter=lambda node, source_bytes: _py_branch_increment(node, source_bytes),
    heuristic_fn_patterns=(r"^\s*def\s+[A-Za-z_][A-Za-z0-9_]*\s*\(",),
    heuristic_branch_patterns=(
        r"\bif\b",
        r"\belif\b",
        r"\bfor\b",
        r"\bwhile\b",
        r"\bexcept\b",
        r"\band\b",
        r"\bor\b",
    ),
    heuristic_nesting_fn=lambda source: _heuristic_py_nesting(source),
)

_PROFILES["rust"] = LanguageProfile(
    name="rust",
    parser=_build_parser(ts_rust.language if ts_rust is not None else None),
    function_nodes=frozenset(_RUST_FUNCTION_NODES),
    branch_nodes=frozenset(_RUST_BRANCH_NODES),
    scope_nodes=frozenset(_RUST_SCOPE_NODES),
    branch_counter=lambda node, source_bytes: _rust_branch_increment(node, source_bytes),
    heuristic_fn_patterns=(r"\bfn\s+[a-zA-Z_]", r"\|[^|]*\|\s*\{"),
    heuristic_branch_patterns=(
        r"\bif\b",
        r"\bmatch\b",
        r"\bfor\b",
        r"\bwhile\b",
        r"\bloop\b",
        r"\bunsafe\b",
    ),
    heuristic_nesting_fn=lambda source: _heuristic_rust_nesting(source),
)


def analyze_files(files: list[SourceFile]) -> dict[str, ComplexityMetrics]:
    metrics: dict[str, ComplexityMetrics] = {}
    for source_file in files:
        result = analyze_file(source_file.abs_path, source_file.language)
        if result.path != source_file.path:
            result = result._replace(path=source_file.path)
        metrics[source_file.path] = result
    return metrics


def analyze_file(abs_path: Path, language: str) -> ComplexityMetrics:
    path = abs_path.as_posix()
    profile = _PROFILES.get(language)
    if profile is None:
        return ComplexityMetrics(
            path=path,
            language=language,
            function_count=0,
            max_cyclomatic=0,
            avg_cyclomatic=0.0,
            max_nesting=0,
            parser_source="skipped",
            parse_ok=True,
        )

    source = _read_source(abs_path)
    source_bytes = source.encode("utf-8", errors="ignore")

    try:
        if profile.parser is None:
            raise RuntimeError(f"{language} parser unavailable")
        tree = profile.parser.parse(source_bytes)
        return _analyze_ast(path, language, source_bytes, tree.root_node, profile)
    except Exception:
        fallback = _heuristic_metrics(path, language, source, profile)
        return fallback._replace(parse_ok=False, parser_source="heuristic")


def _analyze_ast(
    path: str, language: str, source_bytes: bytes, root_node: object, profile: LanguageProfile
) -> ComplexityMetrics:
    functions = _collect_function_nodes(root_node, profile.function_nodes)
    if not functions:
        return ComplexityMetrics(path, language, 0, 0, 0.0, 0, f"{language}_ast", True)

    cyclomatic_scores: list[int] = []
    nesting_scores: list[int] = []
    for function_node in functions:
        cyclomatic, max_nesting = _compute_function_metrics(
            function_node=function_node,
            function_nodes=profile.function_nodes,
            scope_nodes=profile.scope_nodes,
            branch_counter=profile.branch_counter,
            source_bytes=source_bytes,
        )
        cyclomatic_scores.append(cyclomatic)
        nesting_scores.append(max_nesting)

    return ComplexityMetrics(
        path=path,
        language=language,
        function_count=len(functions),
        max_cyclomatic=max(cyclomatic_scores),
        avg_cyclomatic=(sum(cyclomatic_scores) / len(cyclomatic_scores)),
        max_nesting=max(nesting_scores),
        parser_source=f"{language}_ast",
        parse_ok=True,
    )


def _collect_function_nodes(root_node: Any, function_types: frozenset[str]) -> list[Any]:
    functions: list[Any] = []
    stack = [root_node]

    while stack:
        node = stack.pop()
        if node.type in function_types:
            functions.append(node)
        stack.extend(reversed(node.children))

    return functions


def _compute_function_metrics(
    function_node: Any,
    function_nodes: frozenset[str],
    scope_nodes: frozenset[str],
    branch_counter: Callable[[Any, bytes], int],
    source_bytes: bytes,
) -> tuple[int, int]:
    complexity = 1
    max_nesting = 1
    stack: list[tuple[Any, int]] = [(function_node, 0)]

    while stack:
        node, depth = stack.pop()
        for child in node.children:
            if child.type in function_nodes:
                continue
            complexity += int(branch_counter(child, source_bytes))
            next_depth = depth + 1 if child.type in scope_nodes else depth
            if next_depth > max_nesting:
                max_nesting = next_depth
            stack.append((child, next_depth))

    return complexity, max_nesting


def _ts_branch_increment(node: Any, source_bytes: bytes) -> int:
    if node.type in _TS_BRANCH_NODES:
        if node.type == "switch_case":
            return 0 if _is_default_switch_case(node, source_bytes) else 1
        return 1

    if node.type == "binary_expression" and _is_ts_logical_binary(node, source_bytes):
        return 1

    return 0


def _py_branch_increment(node: Any, _source_bytes: bytes) -> int:
    return 1 if node.type in _PY_BRANCH_NODES else 0


def _rust_branch_increment(node: Any, _source_bytes: bytes) -> int:
    return 1 if node.type in _RUST_BRANCH_NODES else 0


def _is_default_switch_case(node: Any, source_bytes: bytes) -> bool:
    for child in node.children:
        if child.type == "default":
            return True

    prefix = source_bytes[node.start_byte : min(node.end_byte, node.start_byte + 32)].lstrip()
    return prefix.startswith(b"default")


def _is_ts_logical_binary(node: Any, source_bytes: bytes) -> bool:
    operator_node = node.child_by_field_name("operator")
    if operator_node is not None:
        operator = source_bytes[operator_node.start_byte : operator_node.end_byte].strip()
        return operator in {b"&&", b"||"}

    for child in node.children:
        if child.type in {"&&", "||"}:
            return True

    snippet = source_bytes[node.start_byte : node.end_byte]
    return b"&&" in snippet or b"||" in snippet


def _heuristic_metrics(
    path: str, language: str, source: str, profile: LanguageProfile
) -> ComplexityMetrics:
    lower_source = source.lower()
    function_count = _count_regex(source, profile.heuristic_fn_patterns)
    branching = _count_regex(lower_source, profile.heuristic_branch_patterns)
    max_nesting = profile.heuristic_nesting_fn(source)

    if function_count <= 0:
        return ComplexityMetrics(path, language, 0, 0, 0.0, 0, "heuristic", False)

    max_cyclomatic = max(1, 1 + branching)
    avg_cyclomatic = max_cyclomatic / function_count
    return ComplexityMetrics(
        path=path,
        language=language,
        function_count=function_count,
        max_cyclomatic=max_cyclomatic,
        avg_cyclomatic=avg_cyclomatic,
        max_nesting=max(1, max_nesting),
        parser_source="heuristic",
        parse_ok=False,
    )


def _count_regex(source: str, patterns: tuple[str, ...]) -> int:
    total = 0
    for pattern in patterns:
        total += len(re.findall(pattern, source, flags=re.MULTILINE))
    return total


def _heuristic_ts_nesting(source: str) -> int:
    depth = 0
    max_depth = 0
    for char in source:
        if char == "{":
            depth += 1
            if depth > max_depth:
                max_depth = depth
        if char == "}":
            depth = max(0, depth - 1)
    return max_depth


def _heuristic_py_nesting(source: str) -> int:
    max_depth = 0
    for raw_line in source.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not re.match(r"^(if|elif|for|while|try|except|with|else)\b", stripped):
            continue
        indent = len(line) - len(line.lstrip(" "))
        depth = (indent // 4) + 1
        if depth > max_depth:
            max_depth = depth
    return max_depth


def _heuristic_rust_nesting(source: str) -> int:
    return _heuristic_ts_nesting(source)


def _read_source(abs_path: Path) -> str:
    try:
        return abs_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
