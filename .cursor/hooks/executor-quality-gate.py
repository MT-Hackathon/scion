#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SUPPORTED_EXTENSIONS = {".py", ".ts", ".js", ".java", ".svelte", ".rs"}
EXCLUDED_PATH_SEGMENTS = {".cursor", ".claude", ".aiassistant", ".venv", "venv", "node_modules", "__pycache__"}
MAX_FUNCTION_LINES = 60
MAX_NESTING_DEPTH = 3
MAX_TYPE_IGNORES = 3
LINTER_TIMEOUT_SECONDS = 10
COVERAGE_TIMEOUT_SECONDS = 120


@dataclass
class Violation:
    message: str
    line: int | None = None


@dataclass
class FileReport:
    path: Path
    violations: list[Violation]
    info: dict[str, int]


def _resolve_workspace_path() -> Path:
    file_path = globals().get("__file__")
    if file_path:
        return Path(file_path).resolve().parents[2]
    return Path.cwd()


WORKSPACE_PATH = _resolve_workspace_path()


def _load_coverage_thresholds(workspace: Path) -> dict[str, int]:
    """Load coverage thresholds from shared config file.

    Falls back to 90% across the board if the file is missing or unreadable.
    """
    defaults = {"lines": 90, "functions": 90, "branches": 90, "statements": 90}
    config_path = workspace / "app" / "coverage-thresholds.json"
    if not config_path.exists():
        return defaults
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return defaults
        return {key: int(data.get(key, defaults[key])) for key in defaults}
    except (json.JSONDecodeError, OSError, ValueError):
        return defaults


def _emit(payload: dict[str, Any]) -> None:
    json.dump(payload, sys.stdout)
    sys.stdout.write("\n")
    sys.stdout.flush()


def _is_completed_event(event: dict[str, Any]) -> bool:
    return event.get("status") == "completed"


def _is_excluded_path(path: Path, workspace: Path) -> bool:
    try:
        relative = path.resolve().relative_to(workspace.resolve())
    except ValueError:
        return False
    return bool(EXCLUDED_PATH_SEGMENTS & set(relative.parts))


def _extract_paths(result_text: str) -> list[Path]:
    if not result_text:
        return []

    candidates: set[str] = set()

    # Backtick-wrapped snippets often contain file paths in structured summaries.
    for match in re.findall(r"`([^`]+)`", result_text):
        candidates.add(match.strip())

    # Bullet-style lines in "Files touched" sections.
    for line in result_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("-"):
            continue
        bullet_text = stripped[1:].strip()
        if bullet_text:
            candidates.add(bullet_text.split(" - ", 1)[0].strip())

    # Fallback token search for path-like strings with supported extensions.
    for match in re.findall(
        r"([A-Za-z]:[\\/][^\s`'\"()]+?\.(?:py|ts|js|java|svelte|rs)|[A-Za-z0-9_./\\-]+?\.(?:py|ts|js|java|svelte|rs))",
        result_text,
        flags=re.IGNORECASE,
    ):
        candidates.add(match.strip())

    resolved_paths: set[Path] = set()
    for raw in candidates:
        cleaned = raw.strip("`'\"()[]{}:,;")
        if not cleaned:
            continue
        candidate = Path(cleaned)
        path = candidate if candidate.is_absolute() else (WORKSPACE_PATH / candidate)
        suffix = path.suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            continue
        resolved_paths.add(path.resolve())

    return sorted(resolved_paths, key=lambda path: str(path).lower())


def _extract_paths_from_transcript(transcript_path: str | None) -> list[Path]:
    """Parse an agent transcript to extract file paths from the final assistant message."""
    if not transcript_path:
        return []
    path = Path(transcript_path)
    if not path.exists() or not path.is_file():
        return []
    try:
        last_assistant_texts: list[str] = []
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("role") != "assistant":
                    continue
                content = entry.get("message", {}).get("content", [])
                message_texts = [
                    block.get("text", "")
                    for block in content
                    if isinstance(block, dict) and block.get("type") == "text"
                ]
                if message_texts:
                    last_assistant_texts = message_texts
        if last_assistant_texts:
            return _extract_paths("\n".join(last_assistant_texts))
    except (OSError, UnicodeDecodeError):
        pass
    return []


def _discover_changed_files(event: dict[str, Any], workspace: Path) -> list[Path]:
    """Discover files changed by the subagent using a priority chain.

    Priority: event result text -> agent transcript -> git working tree changes -> untracked.
    """
    # Priority 1: extract from result text if present
    result_text = str(event.get("result") or "")
    if result_text.strip():
        paths = _extract_paths(result_text)
        if paths:
            return paths

    # Priority 2: parse agent transcript for file paths
    transcript_path = event.get("agent_transcript_path")
    transcript_paths = _extract_paths_from_transcript(transcript_path)
    if transcript_paths:
        return transcript_paths

    # Priority 3: git working tree changes (unstaged + staged), excluding tooling dirs
    try:
        git_result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(workspace),
        )
        if git_result.returncode == 0 and git_result.stdout.strip():
            raw_paths = git_result.stdout.strip().splitlines()
            resolved_diff: list[Path] = []
            for raw in raw_paths:
                path = (workspace / raw.strip()).resolve()
                if path.suffix.lower() in SUPPORTED_EXTENSIONS and not _is_excluded_path(path, workspace):
                    resolved_diff.append(path)
            if resolved_diff:
                return sorted(resolved_diff, key=lambda p: str(p).lower())
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Priority 4: untracked files, excluding tooling dirs
    try:
        git_result = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(workspace),
        )
        if git_result.returncode == 0 and git_result.stdout.strip():
            raw_paths = git_result.stdout.strip().splitlines()
            resolved_untracked: list[Path] = []
            for raw in raw_paths:
                path = (workspace / raw.strip()).resolve()
                if path.suffix.lower() in SUPPORTED_EXTENSIONS and not _is_excluded_path(path, workspace):
                    resolved_untracked.append(path)
            if resolved_untracked:
                return sorted(resolved_untracked, key=lambda p: str(p).lower())
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return []


def _is_test_file(path: Path) -> bool:
    name = path.name.lower()
    parts = set(path.parts)
    return (
        name.endswith("_test.py")
        or (name.startswith("test_") and name.endswith(".py"))
        or name.endswith("_spec.ts")
        or name.endswith(".test.ts")
        or name.endswith("_spec.js")
        or name.endswith(".test.js")
        or ("tests" in parts and name.endswith(".rs"))
    )


def _line_length(start: int | None, end: int | None) -> int:
    if start is None or end is None or end < start:
        return 0
    return end - start + 1


def _python_nesting(function_node: ast.AST) -> tuple[int, int | None]:
    branch_nodes = (ast.If, ast.For, ast.While, ast.Try, ast.With, ast.Match)
    max_depth = 0
    depth_line: int | None = None

    def walk(node: ast.AST, depth: int) -> None:
        nonlocal max_depth, depth_line
        for child in ast.iter_child_nodes(node):
            next_depth = depth + 1 if isinstance(child, branch_nodes) else depth
            if next_depth > max_depth:
                max_depth = next_depth
                depth_line = getattr(child, "lineno", None)
            walk(child, next_depth)

    walk(function_node, 0)
    return max_depth, depth_line


def _build_parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    parents: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    return parents


def _is_const_assignment(node: ast.AST) -> bool:
    if isinstance(node, ast.Assign):
        names = [target.id for target in node.targets if isinstance(target, ast.Name)]
        return bool(names) and all(name.isupper() for name in names)
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return node.target.id.isupper()
    return False


def _analyze_python(path: Path, source: str) -> FileReport:
    violations: list[Violation] = []
    info = {"else_count": 0}
    lines = source.splitlines()
    info["else_count"] = len(
        [line for line in lines if re.search(r"\b(?:else:|elif\b)", line)]
    )

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return FileReport(path=path, violations=[], info=info)

    parents = _build_parent_map(tree)

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            length = _line_length(getattr(node, "lineno", None), getattr(node, "end_lineno", None))
            if length > MAX_FUNCTION_LINES:
                violations.append(
                    Violation(
                        message=(
                            f"Function `{node.name}` is {length} lines "
                            f"(limit: {MAX_FUNCTION_LINES})"
                        ),
                        line=getattr(node, "lineno", None),
                    )
                )
            depth, depth_line = _python_nesting(node)
            if depth > MAX_NESTING_DEPTH:
                violations.append(
                    Violation(
                        message=(
                            f"Nesting depth of {depth} at line {depth_line} "
                            f"(limit: {MAX_NESTING_DEPTH})"
                        ),
                        line=depth_line,
                    )
                )

        if isinstance(node, ast.Call):
            target_name = None
            if isinstance(node.func, ast.Name):
                target_name = node.func.id
            if target_name in {"eval", "exec", "compile"}:
                violations.append(
                    Violation(
                        message=f"`{target_name}()` call at line {node.lineno}",
                        line=node.lineno,
                    )
                )

    type_ignore_count = len(re.findall(r"#\s*type:\s*ignore\b", source))
    if type_ignore_count > MAX_TYPE_IGNORES:
        violations.append(
            Violation(
                message=(
                    f"`# type: ignore` count is {type_ignore_count} "
                    f"(limit: {MAX_TYPE_IGNORES})"
                )
            )
        )

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            value = float(node.value)
            if -1 <= value <= 1:
                continue
            parent = parents.get(node)
            if parent and _is_const_assignment(parent):
                continue
            violations.append(
                Violation(
                    message=f"Potential magic number `{node.value}` at line {node.lineno}",
                    line=node.lineno,
                )
            )
        if (
            isinstance(node, ast.UnaryOp)
            and isinstance(node.op, ast.USub)
            and isinstance(node.operand, ast.Constant)
            and isinstance(node.operand.value, (int, float))
            and not isinstance(node.operand.value, bool)
        ):
            value = -float(node.operand.value)
            if -1 <= value <= 1:
                continue
            parent = parents.get(node)
            if parent and _is_const_assignment(parent):
                continue
            violations.append(
                Violation(
                    message=f"Potential magic number `{value}` at line {node.lineno}",
                    line=node.lineno,
                )
            )

    return FileReport(path=path, violations=violations, info=info)


def _extract_block_length(lines: list[str], start_index: int) -> int:
    open_braces = 0
    seen_open = False
    for index in range(start_index, len(lines)):
        line = lines[index]
        open_braces += line.count("{")
        if line.count("{") > 0:
            seen_open = True
        open_braces -= line.count("}")
        if seen_open and open_braces <= 0:
            return index - start_index + 1
    return 0


def _analyze_js_like(path: Path, source: str) -> FileReport:
    violations: list[Violation] = []
    info = {"else_count": 0}
    lines = source.splitlines()

    function_pattern = re.compile(
        r"\bfunction\b|\=\>\s*\{|\b[A-Za-z_][A-Za-z0-9_]*\s*\([^;]*\)\s*\{"
    )
    declaration_pattern = re.compile(r"\b(class|if|for|while|switch|catch|try)\b")

    for idx, line in enumerate(lines):
        if function_pattern.search(line) and not declaration_pattern.search(line):
            length = _extract_block_length(lines, idx)
            if length > MAX_FUNCTION_LINES:
                violations.append(
                    Violation(
                        message=f"Function block near line {idx + 1} is {length} lines (limit: {MAX_FUNCTION_LINES})",
                        line=idx + 1,
                    )
                )

    current_depth = 0
    max_depth = 0
    max_line = None
    for idx, line in enumerate(lines):
        opens = line.count("{")
        closes = line.count("}")
        current_depth += opens
        if current_depth > max_depth:
            max_depth = current_depth
            max_line = idx + 1
        current_depth -= closes

        if re.search(r"\bvar\s+[A-Za-z_$]", line):
            violations.append(
                Violation(
                    message=f"`var` declaration at line {idx + 1} (use `const` or `let`)",
                    line=idx + 1,
                )
            )
        if re.search(r"\beval\s*\(|\bnew\s+Function\s*\(|\bFunction\s*\(", line):
            violations.append(
                Violation(
                    message=f"Dynamic evaluation usage at line {idx + 1}",
                    line=idx + 1,
                )
            )
        if re.search(r"\belse\b", line):
            info["else_count"] += 1

    if max_depth > MAX_NESTING_DEPTH:
        violations.append(
            Violation(
                message=f"Nesting depth of {max_depth} at line {max_line} (limit: {MAX_NESTING_DEPTH})",
                line=max_line,
            )
        )

    return FileReport(path=path, violations=violations, info=info)


def _extract_svelte_script(source: str) -> str:
    """Extract script content from a Svelte file."""
    blocks: list[str] = []
    for match in re.finditer(r"<script[^>]*>(.*?)</script>", source, re.DOTALL):
        blocks.append(match.group(1))
    return "\n".join(blocks)


def _analyze_java(path: Path, source: str) -> FileReport:
    violations: list[Violation] = []
    info: dict[str, int] = {}
    lines = source.splitlines()

    method_pattern = re.compile(
        r"^\s*(public|private|protected)\s+[\w<>\[\],\s]+\s+\w+\s*\([^)]*\)\s*(?:throws\s+[\w,\s]+)?\{"
    )

    for idx, line in enumerate(lines):
        if method_pattern.search(line):
            length = _extract_block_length(lines, idx)
            if length > MAX_FUNCTION_LINES:
                violations.append(
                    Violation(
                        message=f"Method near line {idx + 1} is {length} lines (limit: {MAX_FUNCTION_LINES})",
                        line=idx + 1,
                    )
                )
            if length > 0:
                method_lines = lines[idx : idx + length]
                current_depth = 0
                max_depth = 0
                max_line: int | None = None
                for method_idx, method_line in enumerate(method_lines):
                    current_depth += method_line.count("{")
                    if current_depth > max_depth:
                        max_depth = current_depth
                        max_line = idx + method_idx + 1
                    current_depth -= method_line.count("}")
                method_nesting = max_depth - 1
                if method_nesting > MAX_NESTING_DEPTH:
                    violations.append(
                        Violation(
                            message=(
                                f"Nesting depth of {method_nesting} at line {max_line} "
                                f"(limit: {MAX_NESTING_DEPTH})"
                            ),
                            line=max_line,
                        )
                    )

    return FileReport(path=path, violations=violations, info=info)


def _analyze_rust(path: Path, source: str) -> FileReport:
    """Rust analysis is handled by cargo clippy at the workspace level.
    Per-file analysis is limited to line count checks."""
    violations: list[Violation] = []
    info: dict[str, int] = {}

    lines = source.splitlines()

    # Check for function length using a simple heuristic
    fn_pattern = re.compile(r"^\s*(pub\s+)?(async\s+)?fn\s+\w+")
    for idx, line in enumerate(lines):
        if fn_pattern.match(line):
            length = _extract_block_length(lines, idx)
            if length > MAX_FUNCTION_LINES:
                violations.append(
                    Violation(
                        message=f"Function near line {idx + 1} is {length} lines (limit: {MAX_FUNCTION_LINES})",
                        line=idx + 1,
                    )
                )

    return FileReport(path=path, violations=violations, info=info)


def _run_ruff(files: list[Path]) -> list[Violation]:
    """Run ruff check on Python files and return violations."""
    if not files:
        return []
    try:
        result = subprocess.run(
            ["ruff", "check", "--output-format=json", "--no-fix", *[str(file) for file in files]],
            capture_output=True,
            text=True,
            timeout=LINTER_TIMEOUT_SECONDS,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []

    if not result.stdout.strip():
        return []

    try:
        findings = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []

    violations: list[Violation] = []
    for finding in findings:
        code = finding.get("code", "")
        message = finding.get("message", "")
        line = finding.get("location", {}).get("row")
        filename = finding.get("filename", "")
        violations.append(
            Violation(
                message=f"ruff {code}: {message} ({Path(filename).name})",
                line=line,
            )
        )
    return violations


def _run_clippy(workspace: Path) -> list[Violation]:
    """Run cargo clippy on the workspace and return violations."""
    cargo_toml = workspace / "Cargo.toml"
    if not cargo_toml.exists():
        return []
    try:
        result = subprocess.run(
            ["cargo", "clippy", "--workspace", "--all-targets", "--message-format=json", "--", "-D", "warnings"],
            capture_output=True,
            text=True,
            timeout=LINTER_TIMEOUT_SECONDS * 3,
            cwd=str(workspace),
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []

    if not result.stdout.strip():
        return []

    violations: list[Violation] = []
    for line in result.stdout.splitlines():
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if msg.get("reason") != "compiler-message":
            continue
        compiler_msg = msg.get("message", {})
        level = compiler_msg.get("level", "")
        if level not in ("error", "warning"):
            continue
        text = compiler_msg.get("message", "")
        spans = compiler_msg.get("spans", [])
        primary_span = next((s for s in spans if s.get("is_primary")), None)
        line_num = primary_span.get("line_start") if primary_span else None
        filename = Path(primary_span.get("file_name", "")).name if primary_span else ""
        violations.append(
            Violation(
                message=f"clippy {level}: {text} ({filename})",
                line=line_num,
            )
        )
    return violations


def _run_eslint(files: list[Path], workspace: Path) -> list[Violation]:
    """Run eslint on JS/TS/Svelte files and return violations."""
    if not files:
        return []
    frontend_dir = workspace / "app" / "frontend"
    if not frontend_dir.is_dir():
        return []
    try:
        result = subprocess.run(
            ["npx", "eslint", "--format=json", "--no-error-on-unmatched-pattern", *[str(file) for file in files]],
            capture_output=True,
            text=True,
            timeout=LINTER_TIMEOUT_SECONDS,
            cwd=str(frontend_dir),
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []

    if not result.stdout.strip():
        return []

    try:
        findings = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []

    violations: list[Violation] = []
    for file_result in findings:
        filename = Path(file_result.get("filePath", "")).name
        for finding in file_result.get("messages", []):
            severity = finding.get("severity", 0)
            if severity < 2:
                continue
            rule_id = finding.get("ruleId", "")
            message = finding.get("message", "")
            line = finding.get("line")
            violations.append(
                Violation(
                    message=f"eslint {rule_id}: {message} ({filename})",
                    line=line,
                )
            )
    return violations


def _detect_stacks(paths: list[Path], workspace: Path) -> dict[str, bool]:
    result = {"backend": False, "frontend": False, "rust": False}

    # Marker-file detection: check what stacks exist in the workspace
    has_cargo = (workspace / "Cargo.toml").exists()
    has_pyproject = (workspace / "app" / "backend" / "pyproject.toml").exists()
    has_package_json = (workspace / "app" / "frontend" / "package.json").exists()

    for path in paths:
        suffix = path.suffix.lower()
        if suffix == ".rs" and has_cargo:
            result["rust"] = True
        elif suffix == ".py" and has_pyproject:
            result["backend"] = True
        elif suffix in {".ts", ".js", ".svelte"} and has_package_json:
            result["frontend"] = True

    return result


def _run_backend_coverage(workspace: Path) -> list[Violation]:
    backend_dir = workspace / "app" / "backend"
    if not backend_dir.is_dir():
        return []
    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "--cov",
                "--cov-report=json",
                "-q",
                "--tb=no",
                "--no-header",
            ],
            capture_output=True,
            text=True,
            timeout=COVERAGE_TIMEOUT_SECONDS,
            cwd=str(backend_dir),
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []

    cov_json = backend_dir / "coverage.json"
    if not cov_json.exists():
        return []

    try:
        cov_data = json.loads(cov_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    totals = cov_data.get("totals", {})
    covered_pct = totals.get("percent_covered", 100.0)
    thresholds = _load_coverage_thresholds(workspace)
    threshold = thresholds["lines"]

    violations: list[Violation] = []
    if covered_pct < threshold:
        violations.append(
            Violation(
                message=(
                    f"Backend test coverage is {covered_pct:.1f}% "
                    f"(threshold: {threshold}%). "
                    "Write tests to restore coverage."
                )
            )
        )

    files_data = cov_data.get("files", {})
    for file_path, file_info in files_data.items():
        file_summary = file_info.get("summary", {})
        file_pct = file_summary.get("percent_covered", 100.0)
        if file_pct < threshold:
            violations.append(
                Violation(
                    message=(
                        f"  {Path(file_path).name}: {file_pct:.1f}% coverage "
                        f"(threshold: {threshold}%)"
                    )
                )
            )

    return violations


def _run_frontend_coverage(workspace: Path) -> list[Violation]:
    frontend_dir = workspace / "app" / "frontend"
    if not frontend_dir.is_dir():
        return []
    try:
        subprocess.run(
            ["npx", "vitest", "run", "--coverage", "--reporter=json"],
            capture_output=True,
            text=True,
            timeout=COVERAGE_TIMEOUT_SECONDS,
            cwd=str(frontend_dir),
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []

    cov_summary = frontend_dir / "coverage" / "coverage-summary.json"
    if not cov_summary.exists():
        return []

    try:
        cov_data = json.loads(cov_summary.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    thresholds = _load_coverage_thresholds(workspace)
    total = cov_data.get("total", {})

    violations: list[Violation] = []
    for metric, threshold in thresholds.items():
        metric_data = total.get(metric, {})
        pct = metric_data.get("pct", 100.0)
        if pct < threshold:
            violations.append(
                Violation(
                    message=(
                        f"Frontend {metric} coverage is {pct:.1f}% "
                        f"(threshold: {threshold}%). "
                        "Write tests to restore coverage."
                    )
                )
            )

    return violations


def _analyze_file(path: Path) -> FileReport | None:
    if not path.exists() or not path.is_file() or _is_test_file(path):
        return None
    try:
        source = path.read_text(encoding="utf-8")
    except Exception:
        return None

    suffix = path.suffix.lower()
    if suffix == ".py":
        return _analyze_python(path, source)
    if suffix == ".svelte":
        return _analyze_js_like(path, _extract_svelte_script(source))
    if suffix in {".ts", ".js"}:
        return _analyze_js_like(path, source)
    if suffix == ".java":
        return _analyze_java(path, source)
    if suffix == ".rs":
        return _analyze_rust(path, source)
    return None


def _format_followup(reports: list[FileReport]) -> str:
    issue_count = sum(len(report.violations) for report in reports)
    lines = [f"**Executor Quality Gate** found {issue_count} issue(s) in the following files:", ""]

    for report in reports:
        file_name = report.path.name
        lines.append(f"**{file_name}** ({len(report.violations)} issues):")
        for violation in report.violations:
            lines.append(f"- {violation.message}")
        if "else_count" in report.info:
            lines.append(f"- Info: `else`/`elif` count = {report.info['else_count']}")
        lines.append("")

    lines.append("Address these findings before routing to QA.")
    return "\n".join(lines)


def main() -> int:
    try:
        raw_input = sys.stdin.read()
        brace = raw_input.find("{")
        if brace > 0:
            raw_input = raw_input[brace:]
        if not raw_input.strip():
            _emit({})
            return 0

        event = json.loads(raw_input)
        if not isinstance(event, dict):
            _emit({})
            return 0

        if not _is_completed_event(event):
            _emit({})
            return 0

        candidate_paths = _discover_changed_files(event, WORKSPACE_PATH)
        if not candidate_paths:
            _emit({})
            return 0

        reports: list[FileReport] = []
        for path in candidate_paths:
            report = _analyze_file(path)
            if report and report.violations:
                reports.append(report)

        py_files = [
            path
            for path in candidate_paths
            if path.suffix.lower() == ".py" and not _is_test_file(path)
        ]
        js_files = [
            path
            for path in candidate_paths
            if path.suffix.lower() in {".ts", ".js", ".svelte"} and not _is_test_file(path)
        ]
        rs_files = [
            path
            for path in candidate_paths
            if path.suffix.lower() == ".rs" and not _is_test_file(path)
        ]

        linter_violations: list[Violation] = []
        linter_violations.extend(_run_ruff(py_files))
        linter_violations.extend(_run_eslint(js_files, WORKSPACE_PATH))
        if rs_files:
            linter_violations.extend(_run_clippy(WORKSPACE_PATH))
        if linter_violations:
            reports.append(
                FileReport(
                    path=Path("linter-findings"),
                    violations=linter_violations,
                    info={},
                )
            )

        stacks = _detect_stacks(candidate_paths, WORKSPACE_PATH)
        coverage_violations: list[Violation] = []
        if stacks["backend"]:
            coverage_violations.extend(_run_backend_coverage(WORKSPACE_PATH))
        if stacks["frontend"]:
            coverage_violations.extend(_run_frontend_coverage(WORKSPACE_PATH))
        if stacks.get("rust"):
            # Rust coverage is CI-tier; skip in hook (too heavy)
            pass
        if coverage_violations:
            reports.append(
                FileReport(
                    path=Path("coverage-findings"),
                    violations=coverage_violations,
                    info={},
                )
            )

        if not reports:
            _emit({})
            return 0

        _emit({"followup_message": _format_followup(reports)})
        return 0
    except Exception:
        _emit({})
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
