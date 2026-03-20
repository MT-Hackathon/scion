#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

"""Package scion skills into upload-ready bundles for hosted AI targets."""

from __future__ import annotations

import argparse
import ast
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import UTC, datetime
import io
import re
from pathlib import Path, PurePosixPath
import subprocess
import sys
from typing import NamedTuple
import zipfile

EXIT_SUCCESS = 0
EXIT_ERROR = 1

CURSOR_DIR = ".cursor"
SKILLS_DIR = f"{CURSOR_DIR}/skills"
SKILL_FILENAME = "SKILL.md"
DEFAULT_REF = "main"
DEFAULT_OUTPUT_ROOT = Path(".rootstock") / "exports"
DEFAULT_DEPTH = "linked"
DEFAULT_INCLUDE_SCRIPTS = "manifest"
DEFAULT_MODE = "auto"
DEFAULT_TIMEOUT_SECONDS = 120
TIMESTAMP_FORMAT = "%Y%m%dT%H%M%SZ"
FRONTMATTER_DELIMITER = "---"
LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


@dataclass(frozen=True)
class TargetSpec:
    """Export target definition."""

    name: str
    default_mode: str
    supports_zip: bool
    max_files: int | None
    max_bytes: int | None
    instruction_filename: str
    notes: str


@dataclass(frozen=True)
class RepoTextFile:
    """Text file loaded from git."""

    path: PurePosixPath
    content: str
    size_bytes: int


@dataclass(frozen=True)
class SkillSummary:
    """Available skill metadata."""

    name: str
    description: str


@dataclass(frozen=True)
class ScriptInfo:
    """Script metadata for manifest/source export."""

    path: PurePosixPath
    name: str
    purpose: str
    content: str
    size_bytes: int


@dataclass(frozen=True)
class SkillBundle:
    """Selected skill plus included supporting files."""

    name: str
    description: str
    skill_doc: RepoTextFile
    resources: tuple[RepoTextFile, ...]
    script_manifest: tuple[ScriptInfo, ...]
    script_sources: tuple[ScriptInfo, ...]
    omitted_references: tuple[str, ...]


@dataclass(frozen=True)
class BundleArtifact:
    """Rendered output artifact."""

    relative_path: PurePosixPath
    content: bytes


@dataclass(frozen=True)
class PreviewReport:
    """Bundle preview metrics."""

    target: TargetSpec
    mode: str
    ref: str
    commit: str
    skills: tuple[SkillBundle, ...]
    artifacts: tuple[BundleArtifact, ...]
    file_count: int
    total_bytes: int
    estimated_tokens: int
    zip_bytes: int | None
    warnings: tuple[str, ...]


class LinkTarget(NamedTuple):
    """Normalized local markdown link target."""

    path: PurePosixPath
    anchor: str | None


TARGETS: dict[str, TargetSpec] = {
    "claude-project": TargetSpec(
        name="claude-project",
        default_mode="files",
        supports_zip=False,
        max_files=None,
        max_bytes=None,
        instruction_filename="CLAUDE_PROJECT_INSTRUCTIONS.md",
        notes="Flat markdown upload set for Claude Projects; zip unsupported.",
    ),
    "perplexity-space": TargetSpec(
        name="perplexity-space",
        default_mode="files",
        supports_zip=False,
        max_files=None,
        max_bytes=None,
        instruction_filename="PERPLEXITY_SPACE_INSTRUCTIONS.md",
        notes="Flat markdown upload set for Perplexity Spaces; zip unsupported.",
    ),
    "chatgpt-gpt": TargetSpec(
        name="chatgpt-gpt",
        default_mode="zip",
        supports_zip=True,
        max_files=20,
        max_bytes=512 * 1024 * 1024,
        instruction_filename="CHATGPT_GPT_INSTRUCTIONS.md",
        notes="Zip-capable Custom GPT target with 20-file / 512MB hard limits.",
    ),
    "gemini-gem": TargetSpec(
        name="gemini-gem",
        default_mode="zip",
        supports_zip=True,
        max_files=10,
        max_bytes=100 * 1024 * 1024,
        instruction_filename="GEMINI_GEM_INSTRUCTIONS.md",
        notes="Zip-capable Gemini Gem target with 10-file / 100MB hard limits.",
    ),
}

PROFILES: dict[str, tuple[str, ...]] = {
    "rootstock-operator": (
        "rootstock",
        "rootstock-mcp",
        "delegation",
        "planning",
        "skill-authoring-patterns",
        "rule-authoring-patterns",
    ),
    "dev-fundamentals": (
        "testing-debugging",
        "error-architecture",
        "rust-development",
        "svelte-ui",
        "git-workflows",
    ),
    "full": (),
}


def log(message: str) -> None:
    """Emit human-readable output to stderr."""
    sys.stderr.write(f"{message}\n")


def fail(message: str) -> int:
    """Emit a standardized failure message."""
    log(f"ERROR: {message}")
    return EXIT_ERROR


def estimate_tokens(text: str) -> int:
    """Estimate token count from text length."""
    if text == "":
        return 0
    return (len(text) + 3) // 4


def slugify_heading(text: str) -> str:
    """Create a stable markdown anchor fragment."""
    cleaned = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    cleaned = re.sub(r"\s+", "-", cleaned)
    cleaned = re.sub(r"-{2,}", "-", cleaned)
    if cleaned == "":
        return "section"
    return cleaned


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="package-skills.py",
        description=(
            "Package scion skills from a pinned git ref into upload-ready bundles "
            "for Claude Projects, ChatGPT GPTs, Gemini Gems, and Perplexity Spaces."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser(
        "list-targets",
        help="List supported export targets and capability limits.",
    )

    list_profiles = subparsers.add_parser(
        "list-profiles",
        help="List built-in export profiles.",
    )
    list_profiles.set_defaults(include_full_profile=True)

    list_skills = subparsers.add_parser(
        "list-skills",
        help="List available skills from the pinned scion ref.",
    )
    add_source_args(list_skills)

    preview = subparsers.add_parser(
        "preview",
        help="Preview bundle size, file count, warnings, and target-cap fit.",
    )
    add_source_args(preview)
    add_bundle_args(preview)

    export = subparsers.add_parser(
        "export",
        help="Write an upload-ready bundle under .rootstock/exports.",
    )
    add_source_args(export)
    add_bundle_args(export)
    export.add_argument(
        "--output-dir",
        type=Path,
        help=(
            "Override export root directory (default: .rootstock/exports under "
            "the scion repo). Target and timestamp are appended beneath it."
        ),
    )
    return parser.parse_args(argv)


def add_source_args(parser: argparse.ArgumentParser) -> None:
    """Add common git-source arguments."""
    parser.add_argument(
        "--scion-repo",
        type=Path,
        required=True,
        help="Path to a local scion git clone.",
    )
    parser.add_argument(
        "--ref",
        default=DEFAULT_REF,
        help=f"Git ref to export from (default: {DEFAULT_REF}).",
    )


def add_bundle_args(parser: argparse.ArgumentParser) -> None:
    """Add bundle selection and transformation arguments."""
    parser.add_argument(
        "--target",
        choices=sorted(TARGETS.keys()),
        required=True,
        help="Hosted AI destination surface.",
    )
    parser.add_argument(
        "--mode",
        choices=("auto", "files", "zip", "single-md"),
        default=DEFAULT_MODE,
        help="Override output mode (default: auto).",
    )
    parser.add_argument(
        "--skill",
        action="append",
        default=[],
        metavar="SKILL_NAME",
        help="Include a specific skill; repeat for multiple skills.",
    )
    parser.add_argument(
        "--profile",
        action="append",
        default=[],
        choices=sorted(PROFILES.keys()),
        help="Include a built-in profile; repeat to union profiles.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Explicitly include all available skills.",
    )
    parser.add_argument(
        "--depth",
        choices=("frontdoor", "linked", "full"),
        default=DEFAULT_DEPTH,
        help="How deeply to follow same-skill references (default: linked).",
    )
    parser.add_argument(
        "--include-scripts",
        choices=("none", "manifest", "source"),
        default=DEFAULT_INCLUDE_SCRIPTS,
        help="Script handling policy (default: manifest).",
    )


def run_git_text(
    repo_path: Path,
    args: list[str],
    allow_failure: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run a git command that returns text output."""
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=DEFAULT_TIMEOUT_SECONDS,
    )
    if completed.returncode == 0:
        return completed
    if allow_failure:
        return completed
    details = completed.stderr.strip() or completed.stdout.strip() or "git command failed"
    raise RuntimeError(f"git {' '.join(args)} failed: {details}")


def run_git_binary(
    repo_path: Path,
    args: list[str],
    stdin_bytes: bytes | None = None,
) -> subprocess.CompletedProcess[bytes]:
    """Run a git command that returns binary output."""
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_path,
        capture_output=True,
        input=stdin_bytes,
        check=False,
        timeout=DEFAULT_TIMEOUT_SECONDS,
    )
    if completed.returncode == 0:
        return completed
    details = completed.stderr.decode("utf-8", "replace").strip()
    if details == "":
        details = completed.stdout.decode("utf-8", "replace").strip()
    if details == "":
        details = "git command failed"
    raise RuntimeError(f"git {' '.join(args)} failed: {details}")


def ensure_directory(path: Path, label: str) -> None:
    """Validate a required directory argument."""
    if not path.exists():
        raise ValueError(f"{label} does not exist: {path}")
    if not path.is_dir():
        raise ValueError(f"{label} is not a directory: {path}")


def ensure_git_repository(repo_path: Path) -> None:
    """Validate that the source path is a git work tree."""
    completed = run_git_text(
        repo_path,
        ["rev-parse", "--is-inside-work-tree"],
        allow_failure=True,
    )
    if completed.returncode != 0:
        raise ValueError(f"Not a git repository: {repo_path}")
    if completed.stdout.strip().lower() != "true":
        raise ValueError(f"Path is not inside a git work tree: {repo_path}")


def resolve_ref(repo_path: Path, ref: str) -> str:
    """Resolve a ref to a commit SHA."""
    normalized = ref.strip()
    if normalized == "":
        raise ValueError("--ref cannot be blank.")
    completed = run_git_text(
        repo_path,
        ["rev-parse", "--verify", f"{normalized}^{{commit}}"],
        allow_failure=True,
    )
    if completed.returncode != 0:
        raise ValueError(f"Git ref does not exist locally: {normalized}")
    return completed.stdout.strip()


def list_skill_paths(repo_path: Path, ref: str) -> list[PurePosixPath]:
    """List all tracked files under .cursor/skills for the ref."""
    completed = run_git_text(
        repo_path,
        ["ls-tree", "-r", "--name-only", ref, "--", SKILLS_DIR],
    )
    result: list[PurePosixPath] = []
    for line in completed.stdout.splitlines():
        value = line.strip()
        if value == "":
            continue
        result.append(PurePosixPath(value))
    return sorted(result)


def batch_read_files(
    repo_path: Path,
    ref: str,
    paths: list[PurePosixPath],
) -> dict[PurePosixPath, RepoTextFile]:
    """Read multiple git blobs in a single cat-file batch."""
    if not paths:
        return {}
    payload = "".join(f"{ref}:{path.as_posix()}\n" for path in paths).encode("utf-8")
    completed = run_git_binary(repo_path, ["cat-file", "--batch"], stdin_bytes=payload)
    raw = completed.stdout
    offset = 0
    result: dict[PurePosixPath, RepoTextFile] = {}

    for path in paths:
        header_end = raw.find(b"\n", offset)
        if header_end < 0:
            raise RuntimeError(f"Incomplete git batch header while reading {path.as_posix()}")
        header = raw[offset:header_end].decode("utf-8", "replace")
        offset = header_end + 1
        if header.endswith(" missing"):
            raise RuntimeError(f"Git object missing at {ref}:{path.as_posix()}")

        parts = header.split(" ")
        if len(parts) != 3:
            raise RuntimeError(f"Unexpected git batch header for {path.as_posix()}: {header}")

        _, object_type, raw_size = parts
        if object_type != "blob":
            raise RuntimeError(f"Expected blob for {path.as_posix()}, got {object_type}")

        size = int(raw_size)
        blob = raw[offset : offset + size]
        offset += size
        if offset >= len(raw) or raw[offset : offset + 1] != b"\n":
            raise RuntimeError(f"Corrupt git batch stream after {path.as_posix()}")
        offset += 1
        if b"\x00" in blob:
            raise ValueError(f"Binary file not supported in skill bundle: {path.as_posix()}")
        result[path] = RepoTextFile(
            path=path,
            content=blob.decode("utf-8", "replace"),
            size_bytes=size,
        )
    return result


def parse_frontmatter(text: str) -> tuple[dict[str, object], str]:
    """Parse simple YAML frontmatter used by skills."""
    lines = text.splitlines()
    if not lines:
        return {}, text
    if lines[0].strip() != FRONTMATTER_DELIMITER:
        return {}, text

    closing_index: int | None = None
    for index in range(1, len(lines)):
        if lines[index].strip() == FRONTMATTER_DELIMITER:
            closing_index = index
            break
    if closing_index is None:
        return {}, text

    metadata: dict[str, object] = {}
    active_list_key: str | None = None
    for raw_line in lines[1:closing_index]:
        line = raw_line.rstrip()
        stripped = line.strip()
        if stripped == "" or stripped.startswith("#"):
            continue
        if stripped.startswith("- ") and active_list_key is not None:
            current = metadata.get(active_list_key, [])
            if not isinstance(current, list):
                current = []
            current.append(normalize_frontmatter_value(stripped[2:].strip()))
            metadata[active_list_key] = current
            continue
        active_list_key = None
        if ":" not in stripped:
            continue
        key, raw_value = stripped.split(":", 1)
        key = key.strip()
        value = raw_value.strip()
        if value == "":
            metadata[key] = []
            active_list_key = key
            continue
        metadata[key] = normalize_frontmatter_value(value)
    body = "\n".join(lines[closing_index + 1 :])
    return metadata, body


def normalize_frontmatter_value(value: str) -> object:
    """Normalize a minimal YAML scalar."""
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if (
        value.startswith('"')
        and value.endswith('"')
        and len(value) >= 2
    ) or (
        value.startswith("'")
        and value.endswith("'")
        and len(value) >= 2
    ):
        return value[1:-1]
    return value


def extract_description(text: str) -> str:
    """Extract skill description from frontmatter."""
    frontmatter, _ = parse_frontmatter(text)
    value = frontmatter.get("description", "")
    if isinstance(value, str):
        return value.strip()
    return ""


def build_skill_summaries(
    repo_path: Path,
    ref: str,
    skill_paths: list[PurePosixPath],
) -> dict[str, SkillSummary]:
    """Build available skill summaries from SKILL.md files."""
    skill_docs = [
        path
        for path in skill_paths
        if len(path.parts) == 4
        and path.parts[0] == CURSOR_DIR
        and path.parts[1] == "skills"
        and path.parts[3] == SKILL_FILENAME
    ]
    contents = batch_read_files(repo_path, ref, skill_docs)
    result: dict[str, SkillSummary] = {}
    for path in skill_docs:
        skill_name = path.parts[2]
        text_file = contents[path]
        result[skill_name] = SkillSummary(
            name=skill_name,
            description=extract_description(text_file.content),
        )
    return result


def resolve_selected_skills(
    args: argparse.Namespace,
    available_skill_names: set[str],
) -> list[str]:
    """Resolve explicit skill selection from skills, profiles, or --all."""
    if not args.all and not args.skill and not args.profile:
        raise ValueError("Select skills with --skill, choose a --profile, or pass --all.")

    selected: set[str] = set()
    if args.all:
        selected.update(available_skill_names)

    for name in args.skill:
        if name not in available_skill_names:
            raise ValueError(f"Unknown skill: {name}")
        selected.add(name)

    for profile_name in args.profile:
        if profile_name == "full":
            selected.update(available_skill_names)
            continue
        for name in PROFILES[profile_name]:
            if name not in available_skill_names:
                raise ValueError(
                    f"Profile {profile_name} references missing skill at {args.ref}: {name}"
                )
            selected.add(name)

    if not selected:
        raise ValueError("Selection resolved to zero skills.")
    return sorted(selected)


def resolve_mode(target: TargetSpec, requested_mode: str) -> str:
    """Resolve final export mode from target defaults and override."""
    if requested_mode == "auto":
        return target.default_mode
    if requested_mode == "zip" and not target.supports_zip:
        raise ValueError(f"Target {target.name} does not support zip export.")
    return requested_mode


def build_skill_file_index(skill_paths: list[PurePosixPath]) -> dict[str, list[PurePosixPath]]:
    """Index all files by skill name."""
    result: dict[str, list[PurePosixPath]] = defaultdict(list)
    for path in skill_paths:
        if len(path.parts) < 4:
            continue
        if path.parts[0] != CURSOR_DIR or path.parts[1] != "skills":
            continue
        result[path.parts[2]].append(path)
    for name in result:
        result[name] = sorted(result[name])
    return dict(result)


def is_script_path(path: PurePosixPath) -> bool:
    """Return whether the path is under scripts/."""
    return len(path.parts) >= 5 and path.parts[3] == "scripts"


def is_skill_doc_path(path: PurePosixPath) -> bool:
    """Return whether the path is the skill front-door doc."""
    return len(path.parts) == 4 and path.parts[3] == SKILL_FILENAME


def is_non_script_support_path(path: PurePosixPath) -> bool:
    """Return whether the path is a non-script support file inside a skill."""
    if is_skill_doc_path(path):
        return False
    return not is_script_path(path)


def normalize_local_link(source_path: PurePosixPath, raw_target: str) -> LinkTarget | None:
    """Resolve a relative markdown link against a source path."""
    target = raw_target.strip()
    if target == "":
        return None
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target):
        return None
    if target.startswith("#"):
        return LinkTarget(path=source_path, anchor=target[1:] or None)

    path_part, _, fragment = target.partition("#")
    normalized = path_part.strip()
    if normalized == "":
        return LinkTarget(path=source_path, anchor=fragment or None)

    base_dir = source_path.parent
    combined = base_dir / PurePosixPath(normalized)
    collapsed = collapse_posix_path(combined)
    return LinkTarget(path=collapsed, anchor=fragment or None)


def collapse_posix_path(path: PurePosixPath) -> PurePosixPath:
    """Normalize . and .. segments in a PurePosixPath."""
    parts: list[str] = []
    for part in path.parts:
        if part in ("", "."):
            continue
        if part == "..":
            if parts and parts[-1] != "..":
                parts.pop()
                continue
            parts.append(part)
            continue
        parts.append(part)
    return PurePosixPath(*parts)


def extract_markdown_links(text: str) -> list[str]:
    """Extract markdown link targets from text."""
    return [target for _, target in LINK_PATTERN.findall(text)]


def select_support_files(
    skill_name: str,
    skill_doc_path: PurePosixPath,
    skill_doc: RepoTextFile,
    support_files: dict[PurePosixPath, RepoTextFile],
    depth: str,
) -> tuple[list[RepoTextFile], list[str]]:
    """Select support files for a skill according to depth."""
    all_files = {skill_doc_path: skill_doc, **support_files}
    if depth == "frontdoor":
        omitted = collect_omitted_references(
            included_paths={skill_doc_path},
            all_known_paths=set(support_files.keys()) | {skill_doc_path},
            files_by_path=all_files,
            seed_paths=[skill_doc_path],
            selected_skill=skill_name,
        )
        return [], omitted

    if depth == "full":
        included = [support_files[path] for path in sorted(support_files.keys())]
        omitted = collect_omitted_references(
            included_paths={skill_doc_path, *support_files.keys()},
            all_known_paths=set(support_files.keys()) | {skill_doc_path},
            files_by_path=all_files,
            seed_paths=[skill_doc_path, *support_files.keys()],
            selected_skill=skill_name,
        )
        return included, omitted

    linked_paths = follow_same_skill_links(skill_doc_path, all_files)
    included = [support_files[path] for path in linked_paths]
    omitted = collect_omitted_references(
        included_paths={skill_doc_path, *linked_paths},
        all_known_paths=set(support_files.keys()) | {skill_doc_path},
        files_by_path=all_files,
        seed_paths=[skill_doc_path, *linked_paths],
        selected_skill=skill_name,
    )
    return included, omitted


def follow_same_skill_links(
    skill_doc_path: PurePosixPath,
    files_by_path: dict[PurePosixPath, RepoTextFile],
) -> list[PurePosixPath]:
    """Recursively follow same-skill links from the front-door skill doc."""
    queue: deque[PurePosixPath] = deque([skill_doc_path])
    visited: set[PurePosixPath] = set()
    included: set[PurePosixPath] = set()
    while queue:
        current = queue.popleft()
        if current in visited:
            continue
        visited.add(current)
        file = files_by_path.get(current)
        if file is None:
            continue
        content = file.content
        if content == "":
            continue
        for raw_target in extract_markdown_links(content):
            normalized = normalize_local_link(current, raw_target)
            if normalized is None:
                continue
            if normalized.path == current:
                continue
            candidate = files_by_path.get(normalized.path)
            if candidate is None:
                continue
            if candidate.path == skill_doc_path:
                continue
            if candidate.path not in included:
                included.add(candidate.path)
                if candidate.path.suffix.lower() == ".md":
                    queue.append(candidate.path)
    return sorted(included)


def collect_omitted_references(
    included_paths: set[PurePosixPath],
    all_known_paths: set[PurePosixPath],
    files_by_path: dict[PurePosixPath, RepoTextFile],
    seed_paths: list[PurePosixPath],
    selected_skill: str,
) -> list[str]:
    """Collect omitted same-skill or cross-skill local references."""
    findings: set[str] = set()
    for source_path in seed_paths:
        file_record = files_by_path.get(source_path)
        if file_record is None:
            continue
        if source_path.suffix.lower() != ".md":
            continue
        for raw_target in extract_markdown_links(file_record.content):
            normalized = normalize_local_link(source_path, raw_target)
            if normalized is None:
                continue
            if normalized.path in included_paths:
                continue
            if normalized.path in all_known_paths:
                findings.add(
                    f"{source_path.as_posix()} -> omitted {normalized.path.as_posix()}"
                )
                continue
            if len(normalized.path.parts) >= 4 and normalized.path.parts[:2] == (CURSOR_DIR, "skills"):
                target_skill = normalized.path.parts[2]
                if target_skill != selected_skill:
                    findings.add(
                        f"{source_path.as_posix()} -> external skill reference {normalized.path.as_posix()}"
                    )
    return sorted(findings)


def extract_script_manifest_entries(skill_doc_text: str) -> dict[str, str]:
    """Parse the Script Manifest table from a skill doc when present."""
    result: dict[str, str] = {}
    lines = skill_doc_text.splitlines()
    in_section = False
    for line in lines:
        if line.startswith("## "):
            if in_section:
                break
            in_section = line.strip() == "## Script Manifest"
            continue
        if not in_section:
            continue
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 2:
            continue
        script_match = re.search(r"`([^`]+)`", cells[0])
        if script_match is not None:
            script_cell = script_match.group(1).strip()
        else:
            script_cell = cells[0].strip().split(" ", 1)[0]
        purpose_cell = cells[1].strip()
        if script_cell == "" or script_cell.lower() == "script":
            continue
        if purpose_cell == "" or purpose_cell == "---":
            continue
        result[script_cell] = purpose_cell
    return result


def extract_python_purpose(content: str) -> str:
    """Extract the first line of a module docstring."""
    try:
        module = ast.parse(content)
    except SyntaxError:
        return ""
    docstring = ast.get_docstring(module)
    if not docstring:
        return ""
    first_line = docstring.strip().splitlines()[0].strip()
    return first_line


def build_script_info(
    skill_doc_text: str,
    script_files: list[RepoTextFile],
) -> list[ScriptInfo]:
    """Build script manifest/source metadata."""
    manifest_entries = extract_script_manifest_entries(skill_doc_text)
    result: list[ScriptInfo] = []
    for script_file in sorted(script_files, key=lambda item: item.path.as_posix()):
        purpose = manifest_entries.get(script_file.path.name, "").strip()
        if purpose == "" and script_file.path.suffix.lower() == ".py":
            purpose = extract_python_purpose(script_file.content)
        if purpose == "":
            purpose = "Purpose not declared in skill manifest."
        result.append(
            ScriptInfo(
                path=script_file.path,
                name=script_file.path.name,
                purpose=purpose,
                content=script_file.content,
                size_bytes=script_file.size_bytes,
            )
        )
    return result


def build_selected_skill_bundles(
    repo_path: Path,
    ref: str,
    selected_skill_names: list[str],
    file_index: dict[str, list[PurePosixPath]],
    depth: str,
    include_scripts: str,
) -> tuple[SkillBundle, ...]:
    """Load all selected skills from git and build bundle records."""
    all_selected_paths: list[PurePosixPath] = []
    for skill_name in selected_skill_names:
        all_selected_paths.extend(file_index.get(skill_name, []))
    loaded = batch_read_files(repo_path, ref, sorted(all_selected_paths))

    bundles: list[SkillBundle] = []
    for skill_name in selected_skill_names:
        paths = file_index.get(skill_name, [])
        skill_doc_path = PurePosixPath(SKILLS_DIR) / skill_name / SKILL_FILENAME
        skill_doc = loaded.get(skill_doc_path)
        if skill_doc is None:
            raise ValueError(f"Selected skill is missing {SKILL_FILENAME}: {skill_name}")

        support_files = {
            path: loaded[path]
            for path in paths
            if path in loaded and is_non_script_support_path(path)
        }
        selected_resources, omitted_references = select_support_files(
            skill_name=skill_name,
            skill_doc_path=skill_doc_path,
            skill_doc=skill_doc,
            support_files=support_files,
            depth=depth,
        )
        script_files = [
            loaded[path]
            for path in paths
            if path in loaded and is_script_path(path)
        ]
        script_infos = build_script_info(skill_doc.content, script_files)
        script_sources: tuple[ScriptInfo, ...] = ()
        if include_scripts == "source":
            script_sources = tuple(script_infos)

        bundles.append(
            SkillBundle(
                name=skill_name,
                description=extract_description(skill_doc.content),
                skill_doc=skill_doc,
                resources=tuple(selected_resources),
                script_manifest=tuple(script_infos),
                script_sources=script_sources,
                omitted_references=tuple(omitted_references),
            )
        )
    return tuple(bundles)


def export_name_for_repo_file(path: PurePosixPath) -> PurePosixPath:
    """Flatten a repo skill path into a bundle filename."""
    skill_name = path.parts[2]
    if is_skill_doc_path(path):
        return PurePosixPath(f"{skill_name}.md")
    if is_script_path(path):
        relative = "-".join(path.parts[4:])
        return PurePosixPath(f"{skill_name}-{relative}")
    relative = "-".join(path.parts[3:])
    return PurePosixPath(f"{skill_name}-{relative}")


def build_file_mapping(skills: tuple[SkillBundle, ...]) -> dict[PurePosixPath, PurePosixPath]:
    """Map source repo paths to exported flat filenames."""
    mapping: dict[PurePosixPath, PurePosixPath] = {}
    for skill in skills:
        mapping[skill.skill_doc.path] = export_name_for_repo_file(skill.skill_doc.path)
        for resource in skill.resources:
            mapping[resource.path] = export_name_for_repo_file(resource.path)
        for script in skill.script_sources:
            mapping[script.path] = export_name_for_repo_file(script.path)
    return mapping


def rewrite_markdown_links(
    content: str,
    source_path: PurePosixPath,
    mapping: dict[PurePosixPath, PurePosixPath],
) -> str:
    """Rewrite local markdown links to flattened export paths."""

    def replace(match: re.Match[str]) -> str:
        label = match.group(1)
        target = match.group(2)
        normalized = normalize_local_link(source_path, target)
        if normalized is None:
            return match.group(0)
        destination = mapping.get(normalized.path)
        if destination is None:
            return match.group(0)
        rewritten = destination.as_posix()
        if normalized.anchor:
            rewritten = f"{rewritten}#{normalized.anchor}"
        return f"[{label}]({rewritten})"

    return LINK_PATTERN.sub(replace, content)


def build_bundle_index(
    target: TargetSpec,
    mode: str,
    ref: str,
    commit: str,
    depth: str,
    include_scripts: str,
    skills: tuple[SkillBundle, ...],
) -> str:
    """Render bundle manifest markdown."""
    lines = [
        "# Skill Bundle Index",
        "",
        "## Provenance",
        "",
        f"- Target: `{target.name}`",
        f"- Mode: `{mode}`",
        f"- Ref: `{ref}`",
        f"- Commit: `{commit}`",
        f"- Depth: `{depth}`",
        f"- Script handling: `{include_scripts}`",
        f"- Built: `{datetime.now(UTC).isoformat()}`",
        "",
        "## Skills",
        "",
    ]
    for skill in skills:
        resource_count = len(skill.resources)
        script_count = len(skill.script_manifest)
        lines.append(f"### `{skill.name}`")
        if skill.description != "":
            lines.append(f"{skill.description}")
            lines.append("")
        lines.append(f"- Front door: `{export_name_for_repo_file(skill.skill_doc.path).as_posix()}`")
        lines.append(f"- Resources included: `{resource_count}`")
        if include_scripts == "manifest":
            lines.append(f"- Scripts represented in manifest: `{script_count}`")
        elif include_scripts == "source":
            lines.append(f"- Script sources included: `{script_count}`")
        else:
            lines.append(f"- Scripts omitted: `{script_count}`")
        if skill.script_manifest and include_scripts != "none":
            lines.append("- Script manifest:")
            for script in skill.script_manifest:
                lines.append(f"  - `{script.name}`: {script.purpose}")
        if skill.omitted_references:
            lines.append("- Omitted references:")
            for item in skill.omitted_references:
                lines.append(f"  - `{item}`")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_target_instructions(
    target: TargetSpec,
    mode: str,
    include_scripts: str,
    skills: tuple[SkillBundle, ...],
) -> str:
    """Render target-specific operator instructions."""
    lines = [
        f"# {target.name} Upload Instructions",
        "",
        f"This bundle is formatted for `{target.name}` in `{mode}` mode.",
        "",
        "## Upload Order",
        "",
    ]
    if mode == "zip":
        lines.append("1. Upload the generated zip file as the knowledge bundle.")
        lines.append("2. Keep the archive intact; do not unzip before upload.")
        lines.append("3. Use the root `README.md` in the archive as the bundle manifest.")
    elif mode == "single-md":
        lines.append("1. Upload the handbook markdown file first.")
        lines.append("2. Upload this instruction file alongside it.")
        lines.append("3. Treat the handbook as the single bundled knowledge source.")
    else:
        lines.append("1. Upload the instruction file first.")
        lines.append("2. Upload `INDEX.md` second so the model sees the bundle map.")
        lines.append("3. Upload the remaining skill and resource markdown files.")
    lines.extend(
        [
            "",
            "## Notes",
            "",
            f"- Selected skills: `{len(skills)}`",
            f"- Script policy: `{include_scripts}`",
            f"- Target notes: {target.notes}",
            "- Progressive disclosure is preserved by keeping skill front doors and supporting resources separate unless `single-md` was explicitly requested.",
            "",
        ]
    )
    if include_scripts == "manifest":
        lines.extend(
            [
                "## Scripts",
                "",
                "Script source is omitted from the bundle. Script names and purposes are documented in the manifest so the hosted target can reason about operator tooling without absorbing implementation code.",
                "",
            ]
        )
    elif include_scripts == "none":
        lines.extend(
            [
                "## Scripts",
                "",
                "Scripts are intentionally omitted from this bundle.",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def build_single_handbook(
    target: TargetSpec,
    ref: str,
    commit: str,
    depth: str,
    include_scripts: str,
    skills: tuple[SkillBundle, ...],
) -> str:
    """Render the single-markdown handbook mode."""
    lines = [
        "# Skill Handbook",
        "",
        "## Provenance",
        "",
        f"- Target: `{target.name}`",
        f"- Ref: `{ref}`",
        f"- Commit: `{commit}`",
        f"- Depth: `{depth}`",
        f"- Script handling: `{include_scripts}`",
        f"- Built: `{datetime.now(UTC).isoformat()}`",
        "",
        "## Bundle Index",
        "",
    ]
    file_anchor_map, fragment_anchor_map = build_handbook_anchor_maps(skills)
    for skill in skills:
        lines.append(
            f"- [`{skill.name}`](#{file_anchor_map[skill.skill_doc.path]}): "
            f"{len(skill.resources)} resources"
        )
    lines.append("")

    for skill in skills:
        lines.append(f"<a id=\"{file_anchor_map[skill.skill_doc.path]}\"></a>")
        lines.append(f"## Skill: `{skill.name}`")
        lines.append("")
        if skill.description != "":
            lines.append(skill.description)
            lines.append("")
        rewritten_skill = rewrite_handbook_links(
            skill.skill_doc.content,
            source_path=skill.skill_doc.path,
            file_anchor_map=file_anchor_map,
            fragment_anchor_map=fragment_anchor_map,
        )
        lines.append(
            inject_handbook_heading_anchors(
                rewritten_skill,
                source_path=skill.skill_doc.path,
                fragment_anchor_map=fragment_anchor_map,
            ).rstrip()
        )
        lines.append("")

        if skill.resources:
            lines.append("### Resources")
            lines.append("")
        for resource in skill.resources:
            lines.append(f"<a id=\"{file_anchor_map[resource.path]}\"></a>")
            lines.append(f"#### `{resource.path.name}`")
            lines.append("")
            rewritten_resource = rewrite_handbook_links(
                resource.content,
                source_path=resource.path,
                file_anchor_map=file_anchor_map,
                fragment_anchor_map=fragment_anchor_map,
            )
            lines.append(
                inject_handbook_heading_anchors(
                    rewritten_resource,
                    source_path=resource.path,
                    fragment_anchor_map=fragment_anchor_map,
                ).rstrip()
            )
            lines.append("")

        lines.append("### Script Notes")
        lines.append("")
        if not skill.script_manifest:
            lines.append("No scripts declared for this skill.")
            lines.append("")
        elif include_scripts == "none":
            lines.append("Scripts omitted from this handbook.")
            lines.append("")
        elif include_scripts == "manifest":
            lines.append("Script source omitted; manifest follows.")
            lines.append("")
            for script in skill.script_manifest:
                lines.append(f"- `{script.name}`: {script.purpose}")
            lines.append("")
        else:
            lines.append("Script source included below.")
            lines.append("")
            for script in skill.script_sources:
                lines.append(f"#### `{script.name}`")
                lines.append("")
                lines.append(f"{script.purpose}")
                lines.append("")
                language = "python" if script.path.suffix.lower() == ".py" else ""
                fence = f"```{language}".rstrip()
                lines.append(fence)
                lines.append(script.content.rstrip())
                lines.append("```")
                lines.append("")

        if skill.omitted_references:
            lines.append("### Omitted References")
            lines.append("")
            for item in skill.omitted_references:
                lines.append(f"- `{item}`")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def rewrite_handbook_links(
    content: str,
    source_path: PurePosixPath,
    file_anchor_map: dict[PurePosixPath, str],
    fragment_anchor_map: dict[tuple[PurePosixPath, str], str],
) -> str:
    """Rewrite local links to handbook anchors when possible."""

    def replace(match: re.Match[str]) -> str:
        label = match.group(1)
        target = match.group(2)
        normalized = normalize_local_link(source_path, target)
        if normalized is None:
            return match.group(0)
        file_anchor = file_anchor_map.get(normalized.path)
        if file_anchor is None:
            return match.group(0)
        if normalized.anchor:
            fragment_anchor = fragment_anchor_map.get((normalized.path, normalized.anchor))
            if fragment_anchor is not None:
                return f"[{label}](#{fragment_anchor})"
        return f"[{label}](#{file_anchor})"

    return LINK_PATTERN.sub(replace, content)


def build_handbook_anchor_maps(
    skills: tuple[SkillBundle, ...],
) -> tuple[dict[PurePosixPath, str], dict[tuple[PurePosixPath, str], str]]:
    """Build stable file and heading anchors for handbook mode."""
    file_anchor_map: dict[PurePosixPath, str] = {}
    fragment_anchor_map: dict[tuple[PurePosixPath, str], str] = {}
    for skill in skills:
        skill_anchor = f"skill-{slugify_heading(skill.name)}"
        file_anchor_map[skill.skill_doc.path] = skill_anchor
        add_heading_anchors(
            source_path=skill.skill_doc.path,
            content=skill.skill_doc.content,
            file_anchor=skill_anchor,
            fragment_anchor_map=fragment_anchor_map,
        )
        for resource in skill.resources:
            label = f"{skill.name}-{resource.path.name}"
            resource_anchor = f"resource-{slugify_heading(label)}"
            file_anchor_map[resource.path] = resource_anchor
            add_heading_anchors(
                source_path=resource.path,
                content=resource.content,
                file_anchor=resource_anchor,
                fragment_anchor_map=fragment_anchor_map,
            )
    return file_anchor_map, fragment_anchor_map


def add_heading_anchors(
    source_path: PurePosixPath,
    content: str,
    file_anchor: str,
    fragment_anchor_map: dict[tuple[PurePosixPath, str], str],
) -> None:
    """Register fragment anchors for markdown headings in a file."""
    for fragment in iter_markdown_heading_fragments(content):
        key = (source_path, fragment)
        if key in fragment_anchor_map:
            continue
        fragment_anchor_map[key] = f"{file_anchor}--{fragment}"


def iter_markdown_heading_fragments(content: str) -> list[str]:
    """Extract markdown heading fragments outside fenced code blocks."""
    fragments: list[str] = []
    in_fence = False
    for raw_line in content.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        heading_match = re.match(r"^(#{1,6})\s+(.*\S)\s*$", raw_line)
        if heading_match is None:
            continue
        heading_text = re.sub(r"\s+#+\s*$", "", heading_match.group(2)).strip()
        if heading_text == "":
            continue
        fragments.append(slugify_heading(heading_text))
    return fragments


def inject_handbook_heading_anchors(
    content: str,
    source_path: PurePosixPath,
    fragment_anchor_map: dict[tuple[PurePosixPath, str], str],
) -> str:
    """Insert explicit anchors before headings so rewritten links stay stable."""
    lines: list[str] = []
    in_fence = False
    injected_fragments: set[str] = set()
    for raw_line in content.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            lines.append(raw_line)
            continue
        if not in_fence:
            heading_match = re.match(r"^(#{1,6})\s+(.*\S)\s*$", raw_line)
            if heading_match is not None:
                heading_text = re.sub(r"\s+#+\s*$", "", heading_match.group(2)).strip()
                if heading_text != "":
                    fragment = slugify_heading(heading_text)
                    if fragment not in injected_fragments:
                        anchor = fragment_anchor_map.get((source_path, fragment))
                        if anchor is not None:
                            lines.append(f"<a id=\"{anchor}\"></a>")
                            injected_fragments.add(fragment)
        lines.append(raw_line)
    return "\n".join(lines)


def render_files_mode(
    target: TargetSpec,
    ref: str,
    commit: str,
    depth: str,
    include_scripts: str,
    skills: tuple[SkillBundle, ...],
) -> tuple[BundleArtifact, ...]:
    """Render flat-file mode artifacts."""
    mapping = build_file_mapping(skills)
    artifacts: list[BundleArtifact] = [
        BundleArtifact(
            relative_path=PurePosixPath("INDEX.md"),
            content=build_bundle_index(
                target=target,
                mode="files",
                ref=ref,
                commit=commit,
                depth=depth,
                include_scripts=include_scripts,
                skills=skills,
            ).encode("utf-8"),
        ),
        BundleArtifact(
            relative_path=PurePosixPath(target.instruction_filename),
            content=build_target_instructions(
                target=target,
                mode="files",
                include_scripts=include_scripts,
                skills=skills,
            ).encode("utf-8"),
        ),
    ]
    for skill in skills:
        artifacts.append(
            BundleArtifact(
                relative_path=mapping[skill.skill_doc.path],
                content=rewrite_markdown_links(
                    skill.skill_doc.content,
                    source_path=skill.skill_doc.path,
                    mapping=mapping,
                ).encode("utf-8"),
            )
        )
        for resource in skill.resources:
            content = resource.content
            if resource.path.suffix.lower() == ".md":
                content = rewrite_markdown_links(
                    content,
                    source_path=resource.path,
                    mapping=mapping,
                )
            artifacts.append(
                BundleArtifact(
                    relative_path=mapping[resource.path],
                    content=content.encode("utf-8"),
                )
            )
        for script in skill.script_sources:
            artifacts.append(
                BundleArtifact(
                    relative_path=mapping[script.path],
                    content=script.content.encode("utf-8"),
                )
            )
    return tuple(artifacts)


def render_zip_mode(
    target: TargetSpec,
    ref: str,
    commit: str,
    depth: str,
    include_scripts: str,
    skills: tuple[SkillBundle, ...],
) -> tuple[BundleArtifact, ...]:
    """Render zip-ready artifacts; caller packs them into the archive."""
    file_artifacts = list(
        render_files_mode(
            target=target,
            ref=ref,
            commit=commit,
            depth=depth,
            include_scripts=include_scripts,
            skills=skills,
        )
    )
    for index, artifact in enumerate(file_artifacts):
        if artifact.relative_path == PurePosixPath("INDEX.md"):
            file_artifacts[index] = BundleArtifact(
                relative_path=PurePosixPath("README.md"),
                content=build_bundle_index(
                    target=target,
                    mode="zip",
                    ref=ref,
                    commit=commit,
                    depth=depth,
                    include_scripts=include_scripts,
                    skills=skills,
                ).encode("utf-8"),
            )
            break
    for index, artifact in enumerate(file_artifacts):
        if artifact.relative_path == PurePosixPath(target.instruction_filename):
            file_artifacts[index] = BundleArtifact(
                relative_path=PurePosixPath(target.instruction_filename),
                content=build_target_instructions(
                    target=target,
                    mode="zip",
                    include_scripts=include_scripts,
                    skills=skills,
                ).encode("utf-8"),
            )
            break
    return tuple(file_artifacts)


def render_single_md_mode(
    target: TargetSpec,
    ref: str,
    commit: str,
    depth: str,
    include_scripts: str,
    skills: tuple[SkillBundle, ...],
) -> tuple[BundleArtifact, ...]:
    """Render handbook mode artifacts."""
    handbook = build_single_handbook(
        target=target,
        ref=ref,
        commit=commit,
        depth=depth,
        include_scripts=include_scripts,
        skills=skills,
    )
    instructions = build_target_instructions(
        target=target,
        mode="single-md",
        include_scripts=include_scripts,
        skills=skills,
    )
    return (
        BundleArtifact(
            relative_path=PurePosixPath("HANDBOOK.md"),
            content=handbook.encode("utf-8"),
        ),
        BundleArtifact(
            relative_path=PurePosixPath(target.instruction_filename),
            content=instructions.encode("utf-8"),
        ),
    )


def build_preview_report(
    target: TargetSpec,
    mode: str,
    ref: str,
    commit: str,
    depth: str,
    include_scripts: str,
    skills: tuple[SkillBundle, ...],
) -> PreviewReport:
    """Build the preview report and enforce target hard limits."""
    if mode == "files":
        artifacts = render_files_mode(target, ref, commit, depth, include_scripts, skills)
    elif mode == "zip":
        artifacts = render_zip_mode(target, ref, commit, depth, include_scripts, skills)
    else:
        artifacts = render_single_md_mode(target, ref, commit, depth, include_scripts, skills)

    file_count = len(artifacts)
    total_bytes = sum(len(artifact.content) for artifact in artifacts)
    estimated_tokens = sum(estimate_tokens(artifact.content.decode("utf-8", "replace")) for artifact in artifacts)
    warnings: list[str] = []
    for skill in skills:
        if skill.omitted_references:
            warnings.append(
                f"{skill.name}: {len(skill.omitted_references)} omitted local references"
            )

    zip_bytes: int | None = None
    if mode == "zip":
        zip_bytes = measure_zip_size(artifacts)
        total_for_limit = zip_bytes
    else:
        total_for_limit = total_bytes

    if target.max_files is not None and file_count > target.max_files:
        raise ValueError(
            f"Preview exceeds {target.name} file limit: {file_count} > {target.max_files}. "
            "Reduce skill count, lower depth, or use a smaller profile."
        )
    if target.max_bytes is not None and total_for_limit > target.max_bytes:
        size_mb = total_for_limit / (1024 * 1024)
        cap_mb = target.max_bytes / (1024 * 1024)
        raise ValueError(
            f"Preview exceeds {target.name} size limit: {size_mb:.2f}MB > {cap_mb:.2f}MB. "
            "Reduce skill count, lower depth, or omit script source."
        )

    return PreviewReport(
        target=target,
        mode=mode,
        ref=ref,
        commit=commit,
        skills=skills,
        artifacts=artifacts,
        file_count=file_count,
        total_bytes=total_bytes,
        estimated_tokens=estimated_tokens,
        zip_bytes=zip_bytes,
        warnings=tuple(warnings),
    )


def measure_zip_size(artifacts: tuple[BundleArtifact, ...]) -> int:
    """Measure archive size for preview enforcement."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for artifact in artifacts:
            archive.writestr(artifact.relative_path.as_posix(), artifact.content)
    return len(buffer.getvalue())


def print_targets() -> None:
    """Print supported targets."""
    for name in sorted(TARGETS.keys()):
        target = TARGETS[name]
        file_cap = "none" if target.max_files is None else str(target.max_files)
        byte_cap = "none" if target.max_bytes is None else f"{target.max_bytes // (1024 * 1024)}MB"
        print(f"{target.name}")
        print(f"  default_mode: {target.default_mode}")
        print(f"  zip_supported: {'yes' if target.supports_zip else 'no'}")
        print(f"  file_limit: {file_cap}")
        print(f"  size_limit: {byte_cap}")
        print(f"  notes: {target.notes}")


def print_profiles() -> None:
    """Print built-in profiles."""
    for name in sorted(PROFILES.keys()):
        skills = PROFILES[name]
        if name == "full":
            print("full")
            print("  alias for: --all")
            continue
        print(name)
        print(f"  skills: {', '.join(skills)}")


def print_skills(skill_summaries: dict[str, SkillSummary]) -> None:
    """Print available skills and descriptions."""
    for name in sorted(skill_summaries.keys()):
        summary = skill_summaries[name]
        print(name)
        if summary.description != "":
            print(f"  description: {summary.description}")


def print_preview(report: PreviewReport) -> None:
    """Print a human-readable preview report."""
    print(f"target: {report.target.name}")
    print(f"mode: {report.mode}")
    print(f"ref: {report.ref}")
    print(f"commit: {report.commit}")
    print(f"skills: {len(report.skills)}")
    print(f"files: {report.file_count}")
    print(f"bytes: {report.total_bytes}")
    print(f"estimated_tokens: {report.estimated_tokens}")
    if report.zip_bytes is not None:
        print(f"zip_bytes: {report.zip_bytes}")
    print("selected_skills:")
    for skill in report.skills:
        print(f"  - {skill.name}")
    if report.warnings:
        print("warnings:")
        for warning in report.warnings:
            print(f"  - {warning}")


def resolve_export_root(scion_repo: Path, output_dir: Path | None) -> Path:
    """Resolve the export root directory before target/timestamp suffixes."""
    if output_dir is None:
        return scion_repo / DEFAULT_OUTPUT_ROOT
    if output_dir.is_absolute():
        return output_dir
    return scion_repo / output_dir


def write_export(
    report: PreviewReport,
    output_root: Path,
) -> Path:
    """Write the export bundle to disk."""
    timestamp = datetime.now(UTC).strftime(TIMESTAMP_FORMAT)
    export_dir = output_root / report.target.name / timestamp
    export_dir.mkdir(parents=True, exist_ok=True)

    if report.mode == "zip":
        zip_path = export_dir / "bundle.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for artifact in report.artifacts:
                archive.writestr(artifact.relative_path.as_posix(), artifact.content)
        return export_dir

    for artifact in report.artifacts:
        destination = export_dir / Path(artifact.relative_path.as_posix())
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(artifact.content)
    return export_dir


def prepare_selection(
    repo_path: Path,
    ref: str,
) -> tuple[dict[str, SkillSummary], dict[str, list[PurePosixPath]]]:
    """Load the available skill universe for the ref."""
    skill_paths = list_skill_paths(repo_path, ref)
    if not skill_paths:
        raise ValueError(f"No files found under {SKILLS_DIR} at ref {ref}.")
    file_index = build_skill_file_index(skill_paths)
    summaries = build_skill_summaries(repo_path, ref, skill_paths)
    return summaries, file_index


def handle_list_skills(args: argparse.Namespace) -> int:
    """Execute list-skills."""
    scion_repo = args.scion_repo.resolve()
    ensure_directory(scion_repo, "--scion-repo")
    ensure_git_repository(scion_repo)
    resolve_ref(scion_repo, args.ref)
    summaries, _ = prepare_selection(scion_repo, args.ref)
    print_skills(summaries)
    return EXIT_SUCCESS


def build_report_from_args(args: argparse.Namespace) -> PreviewReport:
    """Resolve the git source, selection, and preview report from CLI args."""
    scion_repo = args.scion_repo.resolve()
    ensure_directory(scion_repo, "--scion-repo")
    ensure_git_repository(scion_repo)
    commit = resolve_ref(scion_repo, args.ref)
    summaries, file_index = prepare_selection(scion_repo, args.ref)
    selected_skill_names = resolve_selected_skills(args, set(summaries.keys()))
    target = TARGETS[args.target]
    mode = resolve_mode(target, args.mode)
    bundles = build_selected_skill_bundles(
        repo_path=scion_repo,
        ref=args.ref,
        selected_skill_names=selected_skill_names,
        file_index=file_index,
        depth=args.depth,
        include_scripts=args.include_scripts,
    )
    return build_preview_report(
        target=target,
        mode=mode,
        ref=args.ref,
        commit=commit,
        depth=args.depth,
        include_scripts=args.include_scripts,
        skills=bundles,
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        if args.command == "list-targets":
            print_targets()
            return EXIT_SUCCESS
        if args.command == "list-profiles":
            print_profiles()
            return EXIT_SUCCESS
        if args.command == "list-skills":
            return handle_list_skills(args)

        report = build_report_from_args(args)
        if args.command == "preview":
            print_preview(report)
            return EXIT_SUCCESS

        scion_repo = args.scion_repo.resolve()
        output_root = resolve_export_root(scion_repo, args.output_dir)
        export_dir = write_export(report, output_root)
        print_preview(report)
        print(f"export_dir: {export_dir}")
        return EXIT_SUCCESS
    except Exception as exc:  # noqa: BLE001
        return fail(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
