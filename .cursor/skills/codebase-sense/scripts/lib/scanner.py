# pyright: reportMissingImports=false
from __future__ import annotations

from collections import namedtuple
from pathlib import Path

SourceFile = namedtuple("SourceFile", ["path", "abs_path", "loc", "language", "repo"])

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
    ".venv",
    "venv",
}

_COMMENT_PREFIXES = ("//", "#", "/*", "*", "*/")
_MAX_READ_SIZE_BYTES = 50 * 1024

_EXTENSION_MAP: dict[str, str] = {
    ".ts": "typescript",
    ".java": "java",
    ".html": "html",
    ".scss": "scss",
    ".py": "python",
    ".svelte": "svelte",
    ".rs": "rust",
}

_CONFIG_FILES: dict[str, str] = {
    "package.json": "json",
    "angular.json": "json",
    "pom.xml": "xml",
    "Cargo.toml": "toml",
}

_NAME_PREFIX_LANGUAGES: dict[str, str] = {
    "build.gradle": "gradle",
    "tsconfig": "json",
}


def discover_repos(workspace_path: Path) -> list[Path]:
    workspace = workspace_path.resolve()

    workspace_repos = _discover_from_workspace_file(workspace)
    if workspace_repos:
        return sorted(workspace_repos, key=lambda repo: repo.as_posix().lower())

    return [workspace]


def _discover_from_workspace_file(workspace: Path) -> list[Path] | None:
    import json as _json

    candidates = list(workspace.glob("*.code-workspace"))
    if not candidates:
        parent = workspace.parent
        candidates = [
            f for f in parent.glob("*.code-workspace")
            if _workspace_file_references(f, workspace)
        ]
    if not candidates:
        return None

    ws_file = candidates[0]
    try:
        data = _json.loads(ws_file.read_text(encoding="utf-8", errors="ignore"))
    except (OSError, ValueError):
        return None

    folders = data.get("folders")
    if not isinstance(folders, list) or len(folders) < 2:
        return None

    repos: set[Path] = set()
    ws_dir = ws_file.parent
    for entry in folders:
        if not isinstance(entry, dict):
            continue
        folder_path = entry.get("path")
        if not isinstance(folder_path, str):
            continue
        resolved = (ws_dir / folder_path).resolve()
        if resolved.is_dir() and (resolved / ".git").exists():
            repos.add(resolved)

    return sorted(repos) if len(repos) >= 2 else None


def _workspace_file_references(ws_file: Path, workspace: Path) -> bool:
    import json as _json

    try:
        data = _json.loads(ws_file.read_text(encoding="utf-8", errors="ignore"))
    except (OSError, ValueError):
        return False
    folders = data.get("folders")
    if not isinstance(folders, list):
        return False
    ws_dir = ws_file.parent
    for entry in folders:
        if not isinstance(entry, dict):
            continue
        folder_path = entry.get("path")
        if isinstance(folder_path, str) and (ws_dir / folder_path).resolve() == workspace:
            return True
    return False


def scan_files(repos: list[Path]) -> list[SourceFile]:
    if not repos:
        return []

    common_parent = _common_parent(repos)
    scanned: list[SourceFile] = []

    for repo in repos:
        for file_path in _walk_repo_files(repo.resolve()):
            rel_path = file_path.resolve().relative_to(common_parent).as_posix()
            scanned.append(
                SourceFile(
                    path=rel_path,
                    abs_path=file_path.resolve(),
                    loc=_count_loc(file_path),
                    language=_detect_language(file_path),
                    repo=repo.name,
                )
            )

    scanned.sort(key=lambda source_file: source_file.path)
    return scanned


def _walk_repo_files(repo_root: Path) -> list[Path]:
    files: list[Path] = []
    stack = [repo_root]

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

            if is_supported_file(child):
                files.append(child)

    return files


def is_supported_file(file_path: Path) -> bool:
    name = file_path.name
    suffix = file_path.suffix.lower()

    if suffix in _EXTENSION_MAP:
        return True
    if name in _CONFIG_FILES:
        return True
    for prefix in _NAME_PREFIX_LANGUAGES:
        if name.startswith(prefix):
            return True
    return False


def _detect_language(file_path: Path) -> str:
    name = file_path.name
    suffix = file_path.suffix.lower()

    extension_language = _EXTENSION_MAP.get(suffix)
    if extension_language is not None:
        return extension_language
    config_language = _CONFIG_FILES.get(name)
    if config_language is not None:
        return config_language
    for prefix, language in _NAME_PREFIX_LANGUAGES.items():
        if name.startswith(prefix):
            return language
    return "text"


def _count_loc(file_path: Path) -> int:
    try:
        file_size = file_path.stat().st_size
    except OSError:
        return 0

    if file_size > _MAX_READ_SIZE_BYTES:
        return max(1, int(file_size / 40))

    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return 0

    loc = 0
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith(_COMMENT_PREFIXES):
            continue
        loc += 1
    return loc


def _common_parent(paths: list[Path]) -> Path:
    resolved = [path.resolve() for path in paths]
    all_parts = [path.parts for path in resolved]
    shortest = min(len(parts) for parts in all_parts)

    common_parts: list[str] = []
    for index in range(shortest):
        token = all_parts[0][index]
        if all(parts[index] == token for parts in all_parts):
            common_parts.append(token)
        else:
            break

    if not common_parts:
        return resolved[0].parent

    return Path(*common_parts)
