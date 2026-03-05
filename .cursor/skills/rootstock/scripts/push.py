#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

# DEPRECATED: Push is now handled by `graft push` via the graft library.
# This script is retained for backward compatibility only.
# Use: graft push --source-repo <path> [--dry-run]

"""Push a filtered .cursor environment into a contributor branch."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime
import fnmatch
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys

EXIT_SUCCESS = 0
EXIT_ERROR = 1

CURSOR_DIRNAME = ".cursor"
ROOTSTOCKIGNORE_FILENAME = ".rootstockignore"
FRONTMATTER_DELIMITER = "---"

CONTENT_FILTER_TARGETS: set[PurePosixPath] = {
    PurePosixPath("rules/998-temporal-self/RULE.mdc"),
    PurePosixPath("rules/999-codebase-briefing/RULE.mdc"),
}

CONTENT_FILTER_PLACEHOLDER = (
    "<!-- Content is per-user/per-project and excluded from Rootstock sync.\n"
    "     This file's frontmatter (description, activation) syncs; content does not.\n"
    "     See: .cursor/skills/rootstock/resources/curation-protocol.md -->\n"
)

CONTRIBUTOR_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
DATE_FORMAT = "%Y-%m-%d"
GIT_TIMEOUT_SECONDS = 120


@dataclass(frozen=True)
class IgnoreRule:
    """Single .rootstockignore rule."""

    pattern: str
    is_directory: bool


@dataclass(frozen=True)
class CopyAction:
    """Single source-to-destination file copy action."""

    source_path: Path
    relative_path: PurePosixPath
    filtered_content: str | None


def emit_json(payload: dict[str, object]) -> None:
    """Emit machine-readable JSON payload to stdout."""
    print(json.dumps(payload, indent=2))


def log(message: str) -> None:
    """Emit human-readable status to stderr."""
    sys.stderr.write(f"{message}\n")


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        prog="push.py",
        description=(
            "Copy a .cursor environment to contributor/{name} in Rootstock, "
            "respecting .rootstockignore and content filtering rules."
        ),
    )
    parser.add_argument(
        "--source-repo",
        type=Path,
        required=True,
        help="Path to source repository containing .cursor/",
    )
    parser.add_argument(
        "--rootstock-repo",
        type=Path,
        required=True,
        help="Path to local Rootstock repository clone.",
    )
    parser.add_argument(
        "--contributor",
        required=True,
        help="Contributor name used for branch contributor/{name}.",
    )
    parser.add_argument(
        "--project",
        default=None,
        help="Project name for per-project branches (e.g. universal-api). Branch becomes contributor/{name}/{project}.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview copy actions without writing files or changing git state.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logs.",
    )
    return parser.parse_args(argv)


def fail(message: str, payload: dict[str, object] | None = None) -> int:
    """Return standardized failure response."""
    result = payload if payload is not None else {}
    result["status"] = "error"
    result["error"] = message
    emit_json(result)
    log(f"ERROR: {message}")
    return EXIT_ERROR


def validate_contributor_name(raw_name: str) -> str:
    """Validate branch-safe contributor name."""
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


def ensure_file(path: Path, label: str) -> None:
    """Validate that a path exists and is a file."""
    if not path.exists():
        raise ValueError(f"{label} does not exist: {path}")
    if not path.is_file():
        raise ValueError(f"{label} is not a file: {path}")


def run_git(
    repo_path: Path,
    args: list[str],
    verbose: bool,
    allow_failure: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run a git command and return the completed process."""
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
    """Validate that path is a git work tree."""
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


def parse_rootstockignore(ignore_file: Path) -> list[IgnoreRule]:
    """Parse .rootstockignore into rule objects."""
    rules: list[IgnoreRule] = []
    for raw_line in ignore_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line == "":
            continue
        if line.startswith("#"):
            continue
        is_directory = line.endswith("/")
        pattern = line[:-1] if is_directory else line
        if pattern == "":
            continue
        rules.append(IgnoreRule(pattern=pattern, is_directory=is_directory))
    return rules


def glob_match(path: PurePosixPath, pattern: str) -> bool:
    """Match file path against a gitignore-style glob pattern."""
    as_posix = path.as_posix()
    if fnmatch.fnmatch(as_posix, pattern):
        return True
    if fnmatch.fnmatch(path.name, pattern):
        return True
    if path.match(pattern):
        return True
    if "/" not in pattern and path.match(f"**/{pattern}"):
        return True
    return False


def directory_match(path: PurePosixPath, directory_pattern: str) -> bool:
    """Match file path against a directory exclusion pattern."""
    directory = directory_pattern.strip("/")
    if directory == "":
        return False
    if "/" in directory:
        prefix = f"{directory}/"
        path_text = path.as_posix()
        if path_text.startswith(prefix):
            return True
        if path_text == directory:
            return True
        if path.match(f"**/{directory}/**"):
            return True
        if path.match(f"{directory}/**"):
            return True
        return False
    return directory in path.parts


def should_exclude(relative_cursor_path: PurePosixPath, rules: list[IgnoreRule]) -> bool:
    """Return whether a .cursor-relative path should be excluded."""
    repo_relative_path = PurePosixPath(CURSOR_DIRNAME) / relative_cursor_path
    candidates = (relative_cursor_path, repo_relative_path)
    for rule in rules:
        for candidate in candidates:
            if rule.is_directory and directory_match(candidate, rule.pattern):
                return True
            if not rule.is_directory and glob_match(candidate, rule.pattern):
                return True
    return False


def extract_frontmatter(text: str, source_path: Path) -> str:
    """Extract YAML frontmatter content from markdown-like file."""
    lines = text.splitlines()
    if len(lines) < 3:
        raise ValueError(f"Expected YAML frontmatter in {source_path}, but file is too short.")
    if lines[0].strip() != FRONTMATTER_DELIMITER:
        raise ValueError(f"Expected starting frontmatter delimiter in {source_path}.")
    closing_index: int | None = None
    for index in range(1, len(lines)):
        if lines[index].strip() == FRONTMATTER_DELIMITER:
            closing_index = index
            break
    if closing_index is None:
        raise ValueError(f"Expected closing frontmatter delimiter in {source_path}.")
    body = lines[1:closing_index]
    return "\n".join(body).rstrip("\n")


def build_filtered_content(source_text: str, source_path: Path) -> str:
    """Build content-filtered output for rule 998/999 files."""
    frontmatter = extract_frontmatter(source_text, source_path)
    if frontmatter == "":
        return f"{FRONTMATTER_DELIMITER}\n{FRONTMATTER_DELIMITER}\n\n{CONTENT_FILTER_PLACEHOLDER}"
    return (
        f"{FRONTMATTER_DELIMITER}\n"
        f"{frontmatter}\n"
        f"{FRONTMATTER_DELIMITER}\n\n"
        f"{CONTENT_FILTER_PLACEHOLDER}"
    )


def discover_copy_actions(
    source_cursor_dir: Path,
    ignore_rules: list[IgnoreRule],
) -> tuple[list[CopyAction], list[PurePosixPath], list[PurePosixPath]]:
    """Compute copy actions and excluded/content-filtered paths."""
    actions: list[CopyAction] = []
    excluded_paths: list[PurePosixPath] = []
    filtered_paths: list[PurePosixPath] = []
    for source_path in sorted(source_cursor_dir.rglob("*")):
        if not source_path.is_file():
            continue
        relative_path = PurePosixPath(source_path.relative_to(source_cursor_dir).as_posix())
        if should_exclude(relative_path, ignore_rules):
            excluded_paths.append(relative_path)
            continue
        filtered_content: str | None = None
        if relative_path in CONTENT_FILTER_TARGETS:
            source_text = source_path.read_text(encoding="utf-8")
            filtered_content = build_filtered_content(source_text, source_path)
            filtered_paths.append(relative_path)
        actions.append(
            CopyAction(
                source_path=source_path,
                relative_path=relative_path,
                filtered_content=filtered_content,
            )
        )
    return actions, excluded_paths, filtered_paths


def ensure_branch_checked_out(repo_path: Path, branch: str, verbose: bool) -> None:
    """Checkout contributor branch, creating from main if needed."""
    exists = run_git(
        repo_path=repo_path,
        args=["show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
        verbose=verbose,
        allow_failure=True,
    )
    if exists.returncode == 0:
        run_git(repo_path=repo_path, args=["checkout", branch], verbose=verbose)
        return
    main_exists = run_git(
        repo_path=repo_path,
        args=["show-ref", "--verify", "--quiet", "refs/heads/main"],
        verbose=verbose,
        allow_failure=True,
    )
    if main_exists.returncode != 0:
        raise ValueError("Branch 'main' does not exist locally in rootstock repo.")
    run_git(
        repo_path=repo_path,
        args=["checkout", "-b", branch, "main"],
        verbose=verbose,
    )


def apply_copy_actions(
    destination_cursor_dir: Path,
    actions: list[CopyAction],
    dry_run: bool,
    verbose: bool,
) -> None:
    """Apply clean-copy strategy into destination .cursor directory."""
    if dry_run:
        return
    if destination_cursor_dir.exists():
        if verbose:
            log(f"Removing existing directory: {destination_cursor_dir}")
        shutil.rmtree(destination_cursor_dir)
    destination_cursor_dir.mkdir(parents=True, exist_ok=True)
    for action in actions:
        target_path = destination_cursor_dir / Path(action.relative_path.as_posix())
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if action.filtered_content is not None:
            target_path.write_text(action.filtered_content, encoding="utf-8")
            continue
        shutil.copy2(action.source_path, target_path)


def commit_and_push(
    repo_path: Path,
    contributor: str,
    branch: str,
    verbose: bool,
) -> tuple[bool, str | None]:
    """Stage .cursor changes, commit if needed, and push branch."""
    run_git(repo_path=repo_path, args=["add", CURSOR_DIRNAME], verbose=verbose)
    staged = run_git(
        repo_path=repo_path,
        args=["diff", "--cached", "--quiet"],
        verbose=verbose,
        allow_failure=True,
    )
    if staged.returncode == 0:
        return False, None
    if staged.returncode not in (0, 1):
        raise RuntimeError("Unable to determine staged diff state.")
    iso_date = datetime.now(UTC).strftime(DATE_FORMAT)
    commit_message = f"push: {contributor} environment sync {iso_date}"
    run_git(
        repo_path=repo_path,
        args=["commit", "-m", commit_message, "--", CURSOR_DIRNAME],
        verbose=verbose,
    )
    run_git(
        repo_path=repo_path,
        args=["push", "-u", "origin", branch],
        verbose=verbose,
    )
    return True, commit_message


def relative_strings(paths: list[PurePosixPath]) -> list[str]:
    """Convert paths to sorted stable string list."""
    return sorted(path.as_posix() for path in paths)


def print_human_summary(
    contributor: str,
    project: str | None,
    branch: str,
    copied_count: int,
    excluded_count: int,
    filtered_paths: list[PurePosixPath],
    dry_run: bool,
    committed: bool,
) -> None:
    """Emit concise human summary to stderr."""
    mode = "DRY RUN" if dry_run else "APPLIED"
    summary = f"[{mode}] contributor={contributor}"
    if project is not None:
        summary = f"{summary} project={project}"
    log(f"{summary} branch={branch}")
    log(f"Files copied: {copied_count}")
    log(f"Files excluded: {excluded_count}")
    log(f"Content-filtered files: {len(filtered_paths)}")
    for relative_path in relative_strings(filtered_paths):
        log(f"  - {relative_path}")
    if dry_run:
        log("Git operations skipped due to --dry-run.")
        return
    if committed:
        log("Commit and push completed.")
        return
    log("No staged changes under .cursor/. Commit and push skipped.")


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    args = parse_args(sys.argv[1:] if argv is None else argv)
    payload: dict[str, object] = {}
    try:
        contributor = validate_contributor_name(args.contributor)
        source_repo = args.source_repo.resolve()
        rootstock_repo = args.rootstock_repo.resolve()

        ensure_directory(source_repo, "--source-repo")
        ensure_directory(rootstock_repo, "--rootstock-repo")

        source_cursor = source_repo / CURSOR_DIRNAME
        rootstock_cursor = rootstock_repo / CURSOR_DIRNAME
        ignore_file = rootstock_repo / ROOTSTOCKIGNORE_FILENAME

        ensure_directory(source_cursor, "source .cursor directory")
        ensure_file(ignore_file, ROOTSTOCKIGNORE_FILENAME)
        ensure_git_repository(rootstock_repo, args.verbose)

        ignore_rules = parse_rootstockignore(ignore_file)
        actions, excluded_paths, filtered_paths = discover_copy_actions(
            source_cursor_dir=source_cursor,
            ignore_rules=ignore_rules,
        )

        project: str | None = None
        if args.project is not None:
            project_value = args.project.strip()
            if project_value == "" or CONTRIBUTOR_PATTERN.fullmatch(project_value) is None:
                raise ValueError(
                    "--project contains invalid characters. Use letters, numbers, '.', '_' or '-'."
                )
            project = project_value
            branch = f"contributor/{contributor}/{project}"
        else:
            branch = f"contributor/{contributor}"
        committed = False
        commit_message: str | None = None

        if not args.dry_run:
            ensure_branch_checked_out(rootstock_repo, branch, args.verbose)
        apply_copy_actions(
            destination_cursor_dir=rootstock_cursor,
            actions=actions,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
        if not args.dry_run:
            committed, commit_message = commit_and_push(
                repo_path=rootstock_repo,
                contributor=contributor,
                branch=branch,
                verbose=args.verbose,
            )

        files_copied = len(actions)
        files_excluded = len(excluded_paths)
        filtered_list = relative_strings(filtered_paths)
        print_human_summary(
            contributor=contributor,
            project=project,
            branch=branch,
            copied_count=files_copied,
            excluded_count=files_excluded,
            filtered_paths=filtered_paths,
            dry_run=args.dry_run,
            committed=committed,
        )

        payload = {
            "contributor": contributor,
            "branch": branch,
            "files_copied": files_copied,
            "files_excluded": files_excluded,
            "content_filtered": filtered_list,
            "dry_run": args.dry_run,
            "committed": committed,
        }
        if project is not None:
            payload["project"] = project
        if commit_message is not None:
            payload["commit_message"] = commit_message
        emit_json(payload)
        return EXIT_SUCCESS
    except Exception as exc:  # noqa: BLE001
        if "contributor" in payload:
            return fail(str(exc), payload)
        return fail(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
