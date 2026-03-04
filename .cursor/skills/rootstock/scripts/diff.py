#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

"""Generate classified contributor-vs-main diff reports for Rootstock."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

EXIT_SUCCESS = 0
EXIT_ERROR = 1

BASE_BRANCH = "main"
CURSOR_DIRNAME = ".cursor"
DEFAULT_REPORT_DIR = Path(".rootstock") / "reports"
DATE_FORMAT = "%Y-%m-%d"

CONTRIBUTOR_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
GIT_TIMEOUT_SECONDS = 120

OPERATION_ADDED = "added"
OPERATION_MODIFIED = "modified"
OPERATION_DELETED = "deleted"
OPERATION_RENAMED = "renamed"

ARTIFACT_RULE = "rule"
ARTIFACT_RULE_RESOURCE = "rule-resource"
ARTIFACT_RULE_SCRIPT = "rule-script"
ARTIFACT_SKILL_KNOWLEDGE = "skill-knowledge"
ARTIFACT_SKILL_SCRIPT = "skill-script"
ARTIFACT_SKILL_RESOURCE = "skill-resource"
ARTIFACT_AGENT = "agent"
ARTIFACT_HOOK = "hook"
ARTIFACT_CONFIG = "config"

OPERATION_HEADINGS: dict[str, str] = {
    OPERATION_ADDED: "Added",
    OPERATION_MODIFIED: "Modified",
    OPERATION_DELETED: "Deleted",
    OPERATION_RENAMED: "Renamed",
}

TYPE_HEADINGS: dict[str, str] = {
    ARTIFACT_RULE: "Rules",
    ARTIFACT_RULE_RESOURCE: "Rule Resources",
    ARTIFACT_RULE_SCRIPT: "Rule Scripts",
    ARTIFACT_SKILL_KNOWLEDGE: "Skills",
    ARTIFACT_SKILL_SCRIPT: "Skill Scripts",
    ARTIFACT_SKILL_RESOURCE: "Skill Resources",
    ARTIFACT_AGENT: "Agents",
    ARTIFACT_HOOK: "Hooks",
    ARTIFACT_CONFIG: "Config",
}


@dataclass(frozen=True)
class FileChange:
    """Single file change from git name-status output."""

    operation: str
    path: str
    old_path: str | None = None


def emit_json(payload: dict[str, object]) -> None:
    """Emit machine-readable JSON payload to stdout."""
    print(json.dumps(payload, indent=2))


def log(message: str) -> None:
    """Emit human-readable text to stderr."""
    sys.stderr.write(f"{message}\n")


def fail(message: str, payload: dict[str, object] | None = None) -> int:
    """Emit standardized error payload and stderr message."""
    result = payload if payload is not None else {}
    result["status"] = "error"
    result["error"] = message
    emit_json(result)
    log(f"ERROR: {message}")
    return EXIT_ERROR


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="diff.py",
        description=(
            "Compute classified file-level diffs between contributor branches and main, "
            "and write JSON + Markdown reports."
        ),
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--contributor",
        help="Contributor name (resolved to contributor/{name}).",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="Process all local contributor/* branches.",
    )
    parser.add_argument(
        "--rootstock-repo",
        type=Path,
        required=True,
        help="Path to local Rootstock repository clone.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory to write report files (default: .rootstock/reports/ under rootstock repo).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logs.",
    )
    return parser.parse_args(argv)


def validate_contributor_name(raw_name: str) -> str:
    """Validate branch-safe contributor identifier."""
    name = raw_name.strip()
    if name == "":
        raise ValueError("--contributor cannot be blank.")
    if CONTRIBUTOR_PATTERN.fullmatch(name) is None:
        raise ValueError(
            "--contributor contains invalid characters. Use letters, numbers, '.', '_' or '-'."
        )
    return name


def ensure_directory(path: Path, label: str) -> None:
    """Validate that a path exists and is a directory."""
    if not path.exists():
        raise ValueError(f"{label} does not exist: {path}")
    if not path.is_dir():
        raise ValueError(f"{label} is not a directory: {path}")


def run_git(
    repo_path: Path,
    args: list[str],
    verbose: bool,
    allow_failure: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run git command in repository path."""
    command = ["git", *args]
    if verbose:
        log(f"[git] {repo_path}: {' '.join(command)}")
    try:
        completed = subprocess.run(
            command,
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False,
            encoding="utf-8",
            errors="replace",
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"git {' '.join(args)} timed out after {GIT_TIMEOUT_SECONDS}s"
        ) from exc
    if completed.returncode == 0:
        return completed
    if allow_failure:
        return completed
    stderr = completed.stderr.strip()
    stdout = completed.stdout.strip()
    details = stderr if stderr != "" else stdout
    if details == "":
        details = "git command failed without output"
    raise RuntimeError(f"git {' '.join(args)} failed: {details}")


def ensure_git_repository(repo_path: Path, verbose: bool) -> None:
    """Validate that provided path is a git repository."""
    completed = run_git(
        repo_path=repo_path,
        args=["rev-parse", "--is-inside-work-tree"],
        verbose=verbose,
        allow_failure=True,
    )
    if completed.returncode != 0:
        raise ValueError(f"Not a git repository: {repo_path}")
    if completed.stdout.strip().lower() != "true":
        raise ValueError(f"Path is not inside a git work tree: {repo_path}")


def branch_exists(repo_path: Path, branch: str, verbose: bool) -> bool:
    """Check whether a local branch exists."""
    result = run_git(
        repo_path=repo_path,
        args=["show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
        verbose=verbose,
        allow_failure=True,
    )
    return result.returncode == 0


def list_contributor_branches(repo_path: Path, verbose: bool) -> list[str]:
    """List all local contributor/* branches."""
    completed = run_git(
        repo_path=repo_path,
        args=["for-each-ref", "--format=%(refname:short)", "refs/heads/contributor/"],
        verbose=verbose,
    )
    branches = [line.strip() for line in completed.stdout.splitlines() if line.strip() != ""]
    return sorted(branches)


def parse_name_status(output_text: str) -> list[FileChange]:
    """Parse git diff --name-status output into structured changes."""
    changes: list[FileChange] = []
    for raw_line in output_text.splitlines():
        line = raw_line.strip()
        if line == "":
            continue
        parts = line.split("\t")
        status = parts[0]
        if status.startswith("R"):
            if len(parts) < 3:
                raise ValueError(f"Malformed rename record: {line}")
            changes.append(FileChange(operation=OPERATION_RENAMED, path=parts[2], old_path=parts[1]))
            continue
        if len(parts) < 2:
            raise ValueError(f"Malformed name-status record: {line}")
        if status == "A":
            changes.append(FileChange(operation=OPERATION_ADDED, path=parts[1]))
            continue
        if status == "M":
            changes.append(FileChange(operation=OPERATION_MODIFIED, path=parts[1]))
            continue
        if status == "D":
            changes.append(FileChange(operation=OPERATION_DELETED, path=parts[1]))
            continue
        raise ValueError(f"Unsupported git status code: {status}")
    return changes


def strip_cursor_prefix(path_text: str) -> PurePosixPath:
    """Normalize path for classification by removing optional .cursor/ prefix."""
    path = PurePosixPath(path_text)
    if path.parts and path.parts[0] == CURSOR_DIRNAME:
        without_prefix = PurePosixPath(*path.parts[1:])
        return without_prefix
    return path


def classify_artifact(path_text: str) -> str:
    """Classify changed file by artifact type."""
    normalized = strip_cursor_prefix(path_text)
    parts = normalized.parts
    if len(parts) >= 3 and parts[0] == "rules" and parts[2] == "RULE.mdc":
        return ARTIFACT_RULE
    if len(parts) >= 4 and parts[0] == "rules" and parts[2] == "resources":
        return ARTIFACT_RULE_RESOURCE
    if len(parts) >= 4 and parts[0] == "rules" and parts[2] == "scripts":
        return ARTIFACT_RULE_SCRIPT
    if len(parts) >= 3 and parts[0] == "skills" and parts[2] == "SKILL.md":
        return ARTIFACT_SKILL_KNOWLEDGE
    if len(parts) >= 4 and parts[0] == "skills" and parts[2] == "scripts":
        return ARTIFACT_SKILL_SCRIPT
    if len(parts) >= 4 and parts[0] == "skills" and parts[2] == "resources":
        return ARTIFACT_SKILL_RESOURCE
    if len(parts) >= 2 and parts[0] == "agents" and normalized.suffix == ".md":
        return ARTIFACT_AGENT
    if len(parts) >= 2 and parts[0] == "hooks":
        return ARTIFACT_HOOK
    return ARTIFACT_CONFIG


def group_id_for_path(path_text: str) -> str:
    """Group by parent skill/rule directory when applicable."""
    normalized = strip_cursor_prefix(path_text)
    parts = normalized.parts
    if len(parts) >= 2 and parts[0] in {"skills", "rules"}:
        return f"{parts[0]}/{parts[1]}"
    if len(parts) >= 1 and parts[0] in {"agents", "hooks"}:
        return parts[0]
    if len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}"
    if len(parts) == 1:
        return parts[0]
    return "root"


def neighbor_scope_for_path(path_text: str) -> str:
    """Determine canonical-neighbor scope path."""
    normalized = strip_cursor_prefix(path_text)
    parts = normalized.parts
    if len(parts) >= 2 and parts[0] in {"skills", "rules"}:
        return f"{CURSOR_DIRNAME}/{parts[0]}/{parts[1]}"
    if len(parts) >= 1 and parts[0] in {"agents", "hooks"}:
        return f"{CURSOR_DIRNAME}/{parts[0]}"
    original = PurePosixPath(path_text)
    parent = original.parent
    if parent.as_posix() == ".":
        return "."
    return parent.as_posix()


def load_changed_paths_set(changes: list[FileChange]) -> set[str]:
    """Collect changed paths for neighbor exclusion checks."""
    changed: set[str] = set()
    for change in changes:
        changed.add(change.path)
        if change.old_path is not None:
            changed.add(change.old_path)
    return changed


def get_canonical_neighbors(
    repo_path: Path,
    changes: list[FileChange],
    verbose: bool,
) -> dict[str, list[str]]:
    """Get unchanged main-branch files in same parent scope as each change."""
    changed_paths = load_changed_paths_set(changes)
    scope_cache: dict[str, list[str]] = {}
    neighbors_by_path: dict[str, list[str]] = {}
    for change in changes:
        scope = neighbor_scope_for_path(change.path)
        if scope not in scope_cache:
            completed = run_git(
                repo_path=repo_path,
                args=["ls-tree", "-r", "--name-only", BASE_BRANCH, "--", scope],
                verbose=verbose,
            )
            files = [line.strip() for line in completed.stdout.splitlines() if line.strip() != ""]
            scope_cache[scope] = sorted(files)
        neighbors = [file_path for file_path in scope_cache[scope] if file_path not in changed_paths]
        neighbors_by_path[change.path] = neighbors
    return neighbors_by_path


def get_diff_content(repo_path: Path, branch: str, change: FileChange, verbose: bool) -> str:
    """Load file diff content or full file content for added files."""
    if change.operation == OPERATION_ADDED:
        completed = run_git(
            repo_path=repo_path,
            args=["show", f"{branch}:{change.path}"],
            verbose=verbose,
            allow_failure=True,
        )
        if completed.returncode != 0:
            return ""
        return completed.stdout
    if change.operation == OPERATION_RENAMED and change.old_path is not None:
        completed = run_git(
            repo_path=repo_path,
            args=["diff", "-M", f"{BASE_BRANCH}..{branch}", "--", change.old_path, change.path],
            verbose=verbose,
            allow_failure=True,
        )
        if completed.returncode != 0:
            return ""
        return completed.stdout
    completed = run_git(
        repo_path=repo_path,
        args=["diff", f"{BASE_BRANCH}..{branch}", "--", change.path],
        verbose=verbose,
        allow_failure=True,
    )
    if completed.returncode != 0:
        return ""
    return completed.stdout


def dominant_artifact_type(changes: list[dict[str, object]]) -> str:
    """Return dominant artifact type in a grouped change list."""
    types = [str(item["artifact_type"]) for item in changes]
    if not types:
        return ARTIFACT_CONFIG
    counter = Counter(types)
    return counter.most_common(1)[0][0]


def build_markdown_report(
    contributor: str,
    timestamp: str,
    changes: list[dict[str, object]],
    operation_counts: Counter[str],
    type_counts: Counter[str],
) -> str:
    """Create human-readable markdown report body."""
    lines: list[str] = []
    lines.append(f"# Diff Report: {contributor} vs {BASE_BRANCH}")
    lines.append("")
    lines.append(f"Generated: {timestamp}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Count |")
    lines.append("|--------|-------|")
    lines.append(f"| Total changes | {len(changes)} |")
    lines.append(f"| Added | {operation_counts.get(OPERATION_ADDED, 0)} |")
    lines.append(f"| Modified | {operation_counts.get(OPERATION_MODIFIED, 0)} |")
    lines.append(f"| Deleted | {operation_counts.get(OPERATION_DELETED, 0)} |")
    lines.append(f"| Renamed | {operation_counts.get(OPERATION_RENAMED, 0)} |")
    lines.append("")
    lines.append("## Changes by Type")
    lines.append("")

    changes_by_type: dict[str, list[dict[str, object]]] = defaultdict(list)
    for change in changes:
        artifact_type = str(change["artifact_type"])
        changes_by_type[artifact_type].append(change)

    ordered_types = list(TYPE_HEADINGS.keys())
    for artifact_type in ordered_types:
        typed_changes = changes_by_type.get(artifact_type, [])
        count = type_counts.get(artifact_type, 0)
        heading = TYPE_HEADINGS[artifact_type]
        lines.append(f"### {heading} ({count} changes)")
        if not typed_changes:
            lines.append("- None")
            lines.append("")
            continue
        for change in sorted(typed_changes, key=lambda item: str(item["path"])):
            operation = str(change["operation"])
            path_text = str(change["path"])
            lines.append(f"- [{operation}] `{path_text}`")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def resolve_output_dir(rootstock_repo: Path, output_dir: Path | None) -> Path:
    """Resolve report output directory path."""
    if output_dir is None:
        return rootstock_repo / DEFAULT_REPORT_DIR
    if output_dir.is_absolute():
        return output_dir
    return rootstock_repo / output_dir


def parse_branch_to_contributor(branch: str) -> str:
    """Extract contributor name from contributor/{name} branch."""
    prefix = "contributor/"
    if not branch.startswith(prefix):
        raise ValueError(f"Branch does not follow contributor/* pattern: {branch}")
    name = branch[len(prefix) :].strip()
    if name == "":
        raise ValueError(f"Branch contributor name is empty: {branch}")
    return name


def collect_branch_changes(repo_path: Path, branch: str, verbose: bool) -> list[FileChange]:
    """Collect parsed file changes from main..branch."""
    completed = run_git(
        repo_path=repo_path,
        args=["diff", "-M", "--name-status", f"{BASE_BRANCH}..{branch}"],
        verbose=verbose,
    )
    return parse_name_status(completed.stdout)


def report_for_branch(
    rootstock_repo: Path,
    output_dir: Path,
    branch: str,
    contributor: str,
    verbose: bool,
) -> dict[str, object]:
    """Generate JSON and Markdown reports for one contributor branch."""
    timestamp = datetime.now(UTC).isoformat()
    date_token = datetime.now(UTC).strftime(DATE_FORMAT)

    changes_raw = collect_branch_changes(rootstock_repo, branch, verbose)
    neighbors_by_path = get_canonical_neighbors(rootstock_repo, changes_raw, verbose)

    change_records: list[dict[str, object]] = []
    operation_counts: Counter[str] = Counter()
    type_counts: Counter[str] = Counter()
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)

    for change in changes_raw:
        artifact_type = classify_artifact(change.path)
        operation_counts[change.operation] += 1
        type_counts[artifact_type] += 1
        record: dict[str, object] = {
            "path": change.path,
            "operation": change.operation,
            "artifact_type": artifact_type,
            "diff_content": get_diff_content(rootstock_repo, branch, change, verbose),
            "canonical_neighbors": neighbors_by_path.get(change.path, []),
        }
        if change.old_path is not None:
            record["old_path"] = change.old_path
        change_records.append(record)
        group_id = group_id_for_path(change.path)
        grouped[group_id].append(record)

    change_groups: list[dict[str, object]] = []
    for group_id in sorted(grouped.keys()):
        grouped_changes = grouped[group_id]
        change_groups.append(
            {
                "group_id": group_id,
                "artifact_type": dominant_artifact_type(grouped_changes),
                "changes": grouped_changes,
            }
        )

    metadata = {
        "contributor": contributor,
        "branch": branch,
        "base": BASE_BRANCH,
        "timestamp": timestamp,
        "total_changes": len(change_records),
        "by_operation": {
            OPERATION_ADDED: operation_counts.get(OPERATION_ADDED, 0),
            OPERATION_MODIFIED: operation_counts.get(OPERATION_MODIFIED, 0),
            OPERATION_DELETED: operation_counts.get(OPERATION_DELETED, 0),
            OPERATION_RENAMED: operation_counts.get(OPERATION_RENAMED, 0),
        },
        "by_type": {artifact_type: count for artifact_type, count in sorted(type_counts.items())},
    }
    report_json = {
        "metadata": metadata,
        "change_groups": change_groups,
    }

    markdown = build_markdown_report(
        contributor=contributor,
        timestamp=timestamp,
        changes=change_records,
        operation_counts=operation_counts,
        type_counts=type_counts,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{contributor}-diff-{date_token}.json"
    markdown_path = output_dir / f"{contributor}-diff-{date_token}.md"
    json_path.write_text(json.dumps(report_json, indent=2), encoding="utf-8")
    markdown_path.write_text(markdown, encoding="utf-8")

    log(markdown.rstrip("\n"))
    return {
        "contributor": contributor,
        "branch": branch,
        "json_report": str(json_path.resolve()),
        "markdown_report": str(markdown_path.resolve()),
        "total_changes": len(change_records),
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    args = parse_args(sys.argv[1:] if argv is None else argv)
    payload: dict[str, object] = {}
    try:
        rootstock_repo = args.rootstock_repo.resolve()
        ensure_directory(rootstock_repo, "--rootstock-repo")
        ensure_git_repository(rootstock_repo, args.verbose)
        if not branch_exists(rootstock_repo, BASE_BRANCH, args.verbose):
            raise ValueError("Local base branch 'main' does not exist in rootstock repo.")

        output_dir = resolve_output_dir(rootstock_repo, args.output_dir)

        branches: list[str] = []
        contributor_by_branch: dict[str, str] = {}
        if args.all:
            branches = list_contributor_branches(rootstock_repo, args.verbose)
            if not branches:
                raise ValueError("No local contributor/* branches found.")
            for branch in branches:
                contributor_by_branch[branch] = parse_branch_to_contributor(branch)
        else:
            contributor = validate_contributor_name(args.contributor)
            branch = f"contributor/{contributor}"
            if not branch_exists(rootstock_repo, branch, args.verbose):
                raise ValueError(f"Contributor branch does not exist: {branch}")
            branches = [branch]
            contributor_by_branch[branch] = contributor

        reports: list[dict[str, object]] = []
        for index, branch in enumerate(branches):
            if index > 0:
                log("")
                log("=" * 80)
                log("")
            contributor = contributor_by_branch[branch]
            reports.append(
                report_for_branch(
                    rootstock_repo=rootstock_repo,
                    output_dir=output_dir,
                    branch=branch,
                    contributor=contributor,
                    verbose=args.verbose,
                )
            )

        payload = {
            "status": "ok",
            "base": BASE_BRANCH,
            "report_count": len(reports),
            "reports": reports,
        }
        emit_json(payload)
        return EXIT_SUCCESS
    except Exception as exc:  # noqa: BLE001
        return fail(str(exc), payload if payload else None)


if __name__ == "__main__":
    raise SystemExit(main())
