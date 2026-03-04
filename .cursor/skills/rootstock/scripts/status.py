#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

"""Report Rootstock operational status at a glance."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import subprocess
import sys

EXIT_SUCCESS = 0
EXIT_ERROR = 1

BASE_BRANCH = "main"
CURSOR_DIRNAME = ".cursor"
CONTRIBUTOR_PREFIX = "contributor/"
REPORTS_RELATIVE = Path(".rootstock") / "reports"
RECENT_REPORT_LIMIT = 20
STALE_BEHIND_THRESHOLD = 10
GIT_TIMEOUT_SECONDS = 120


def emit_json(payload: dict[str, object]) -> None:
    """Emit machine-readable JSON payload to stdout."""
    print(json.dumps(payload, indent=2))


def log(message: str) -> None:
    """Emit human-readable status to stderr."""
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
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        prog="status.py",
        description=(
            "Show Rootstock operational status: canonical branch health, contributor "
            "branch lag, and report recency."
        ),
    )
    parser.add_argument(
        "--rootstock-repo",
        type=Path,
        required=True,
        help="Path to local Rootstock repository clone.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logs.",
    )
    return parser.parse_args(argv)


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


def branch_exists(repo_path: Path, branch: str, verbose: bool) -> bool:
    """Check whether local branch exists."""
    completed = run_git(
        repo_path=repo_path,
        args=["show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
        verbose=verbose,
        allow_failure=True,
    )
    return completed.returncode == 0


def estimate_tokens(char_count: int) -> int:
    """Estimate tokens using rough 4 chars/token conversion."""
    if char_count <= 0:
        return 0
    return (char_count + 3) // 4


def list_cursor_files(repo_path: Path, branch: str, verbose: bool) -> list[str]:
    """List tracked .cursor files on branch."""
    completed = run_git(
        repo_path=repo_path,
        args=["ls-tree", "-r", "--name-only", branch, CURSOR_DIRNAME],
        verbose=verbose,
    )
    return sorted([line.strip() for line in completed.stdout.splitlines() if line.strip() != ""])


def read_branch_file(repo_path: Path, branch: str, path_text: str, verbose: bool) -> str:
    """Read branch file content via git show."""
    completed = run_git(
        repo_path=repo_path,
        args=["show", f"{branch}:{path_text}"],
        verbose=verbose,
    )
    return completed.stdout


def main_commit_info(repo_path: Path, branch: str, verbose: bool) -> tuple[str, str]:
    """Return commit ISO date and subject for branch head."""
    completed = run_git(
        repo_path=repo_path,
        args=["log", "-1", "--format=%cI%n%s", branch],
        verbose=verbose,
    )
    lines = [line.rstrip() for line in completed.stdout.splitlines()]
    if len(lines) < 2:
        raise ValueError(f"Unable to read last commit details for branch {branch}.")
    commit_date = lines[0].strip()
    commit_subject = lines[1].strip()
    if commit_date == "" or commit_subject == "":
        raise ValueError(f"Branch {branch} has incomplete commit metadata.")
    return commit_date, commit_subject


def list_contributor_branches(repo_path: Path, verbose: bool) -> list[str]:
    """List all local contributor/* branches including nested names."""
    completed = run_git(
        repo_path=repo_path,
        args=["for-each-ref", "--format=%(refname:short)", "refs/heads/contributor/"],
        verbose=verbose,
    )
    return sorted([line.strip() for line in completed.stdout.splitlines() if line.strip() != ""])


def branch_commits_behind_main(repo_path: Path, branch: str, verbose: bool) -> int:
    """Count commits branch is behind main."""
    completed = run_git(
        repo_path=repo_path,
        args=["rev-list", "--count", f"{branch}..{BASE_BRANCH}"],
        verbose=verbose,
    )
    text = completed.stdout.strip()
    if text == "":
        return 0
    return int(text)


def branch_diff_stat(repo_path: Path, branch: str, verbose: bool) -> tuple[str, int]:
    """Return git diff --stat output and changed file count."""
    completed = run_git(
        repo_path=repo_path,
        args=["diff", "--stat", f"{BASE_BRANCH}..{branch}"],
        verbose=verbose,
    )
    stat_text = completed.stdout.rstrip()
    changed_files = 0
    for line in stat_text.splitlines():
        if "|" in line:
            changed_files += 1
    return stat_text, changed_files


def branch_contributor_name(branch: str) -> str:
    """Extract contributor suffix from contributor/* branch."""
    if branch.startswith(CONTRIBUTOR_PREFIX):
        suffix = branch[len(CONTRIBUTOR_PREFIX) :].strip()
        if suffix != "":
            return suffix
    return branch


def iso_mtime(path: Path) -> str:
    """Convert file mtime to UTC ISO string."""
    ts = datetime.fromtimestamp(path.stat().st_mtime, UTC)
    return ts.isoformat()


def read_reports_status(rootstock_repo: Path) -> dict[str, object]:
    """Inspect .rootstock/reports directory and summarize recency."""
    reports_dir = rootstock_repo / REPORTS_RELATIVE
    if not reports_dir.exists() or not reports_dir.is_dir():
        return {
            "exists": False,
            "path": str(reports_dir.resolve()),
            "recent_reports": [],
            "last_diff_report": None,
            "last_curation_report": None,
        }

    report_files = [path for path in reports_dir.iterdir() if path.is_file()]
    ordered = sorted(report_files, key=lambda path: path.stat().st_mtime, reverse=True)

    recent_reports: list[dict[str, str]] = []
    for report_path in ordered[:RECENT_REPORT_LIMIT]:
        recent_reports.append(
            {
                "name": report_path.name,
                "modified_at": iso_mtime(report_path),
            }
        )

    diff_candidates = [
        path for path in ordered if "-diff-" in path.name and path.suffix.lower() in {".json", ".md"}
    ]
    curation_candidates = [
        path
        for path in ordered
        if "-curation-" in path.name and path.suffix.lower() in {".json", ".md"}
    ]
    last_diff_report = (
        {"name": diff_candidates[0].name, "modified_at": iso_mtime(diff_candidates[0])}
        if diff_candidates
        else None
    )
    last_curation_report = (
        {
            "name": curation_candidates[0].name,
            "modified_at": iso_mtime(curation_candidates[0]),
        }
        if curation_candidates
        else None
    )
    return {
        "exists": True,
        "path": str(reports_dir.resolve()),
        "recent_reports": recent_reports,
        "last_diff_report": last_diff_report,
        "last_curation_report": last_curation_report,
    }


def compute_main_status(repo_path: Path, verbose: bool) -> dict[str, object]:
    """Build canonical main branch status details."""
    main_exists = branch_exists(repo_path, BASE_BRANCH, verbose)
    if not main_exists:
        return {
            "exists": False,
            "branch": BASE_BRANCH,
            "last_commit_date": None,
            "last_commit_message": None,
            "cursor_file_count": 0,
            "cursor_estimated_tokens": 0,
            "cursor_total_chars": 0,
        }

    commit_date, commit_message = main_commit_info(repo_path, BASE_BRANCH, verbose)
    cursor_files = list_cursor_files(repo_path, BASE_BRANCH, verbose)
    total_chars = 0
    for path_text in cursor_files:
        total_chars += len(read_branch_file(repo_path, BASE_BRANCH, path_text, verbose))

    return {
        "exists": True,
        "branch": BASE_BRANCH,
        "last_commit_date": commit_date,
        "last_commit_message": commit_message,
        "cursor_file_count": len(cursor_files),
        "cursor_estimated_tokens": estimate_tokens(total_chars),
        "cursor_total_chars": total_chars,
    }


def compute_contributor_status(repo_path: Path, verbose: bool) -> list[dict[str, object]]:
    """Build per-branch contributor status records."""
    branches = list_contributor_branches(repo_path, verbose)
    records: list[dict[str, object]] = []
    for branch in branches:
        commit_date, commit_message = main_commit_info(repo_path, branch, verbose)
        behind = branch_commits_behind_main(repo_path, branch, verbose)
        diff_stat, changed_files = branch_diff_stat(repo_path, branch, verbose)
        records.append(
            {
                "branch": branch,
                "contributor": branch_contributor_name(branch),
                "last_commit_date": commit_date,
                "last_commit_message": commit_message,
                "commits_behind_main": behind,
                "stale": behind > STALE_BEHIND_THRESHOLD,
                "changed_files_vs_main": changed_files,
                "diff_stat": diff_stat,
            }
        )
    return records


def compute_health(
    main_status: dict[str, object],
    contributors: list[dict[str, object]],
    reports: dict[str, object],
) -> dict[str, object]:
    """Derive high-level operational state."""
    main_exists = bool(main_status.get("exists", False))
    cursor_file_count_raw = main_status.get("cursor_file_count", 0)
    cursor_file_count = cursor_file_count_raw if isinstance(cursor_file_count_raw, int) else 0
    stale_branches = [
        str(item.get("branch", ""))
        for item in contributors
        if bool(item.get("stale", False))
    ]
    recent_reports = reports.get("recent_reports", [])
    report_count = len(recent_reports) if isinstance(recent_reports, list) else 0
    has_reports = bool(reports.get("exists", False)) and report_count > 0

    if not main_exists or cursor_file_count == 0:
        return {
            "state": "Not initialized",
            "reasons": [
                "main branch missing or .cursor content is empty",
            ],
            "stale_branches": stale_branches,
        }

    reasons: list[str] = []
    if stale_branches:
        reasons.append("one or more contributor branches are significantly behind main")
    if not has_reports:
        reasons.append("no reports found in .rootstock/reports")
    if reasons:
        return {
            "state": "Needs attention",
            "reasons": reasons,
            "stale_branches": stale_branches,
        }
    return {
        "state": "Operational",
        "reasons": [],
        "stale_branches": [],
    }


def print_human_dashboard(
    main_status: dict[str, object],
    contributors: list[dict[str, object]],
    reports: dict[str, object],
    health: dict[str, object],
) -> None:
    """Emit concise stderr dashboard."""
    log("Rootstock Status")
    log("=" * 80)
    log(f"Health: {health.get('state', 'unknown')}")
    reasons = health.get("reasons", [])
    if isinstance(reasons, list):
        for reason in reasons:
            log(f"- {reason}")
    log("")

    log("Canonical main")
    if not bool(main_status.get("exists", False)):
        log("- main branch not found locally")
    else:
        log(f"- last commit: {main_status.get('last_commit_date', '')}")
        log(f"- message: {main_status.get('last_commit_message', '')}")
        log(f"- .cursor files: {main_status.get('cursor_file_count', 0)}")
        log(f"- estimated tokens: {main_status.get('cursor_estimated_tokens', 0)}")
    log("")

    log("Contributor branches")
    if not contributors:
        log("- none")
    else:
        for item in contributors:
            stale_flag = " [STALE]" if bool(item.get("stale", False)) else ""
            log(
                f"- {item.get('branch', '')}: behind={item.get('commits_behind_main', 0)} "
                f"changed_files={item.get('changed_files_vs_main', 0)}{stale_flag}"
            )
    log("")

    log("Reports")
    if not bool(reports.get("exists", False)):
        log("- .rootstock/reports not found")
    else:
        recent_reports = reports.get("recent_reports", [])
        report_count = len(recent_reports) if isinstance(recent_reports, list) else 0
        log(f"- recent reports listed: {report_count}")
        last_diff = reports.get("last_diff_report")
        last_curation = reports.get("last_curation_report")
        if isinstance(last_diff, dict):
            log(
                f"- last diff report: {last_diff.get('name', '')} "
                f"({last_diff.get('modified_at', '')})"
            )
        else:
            log("- last diff report: none")
        if isinstance(last_curation, dict):
            log(
                f"- last curation report: {last_curation.get('name', '')} "
                f"({last_curation.get('modified_at', '')})"
            )
        else:
            log("- last curation report: none")


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    args = parse_args(sys.argv[1:] if argv is None else argv)
    payload: dict[str, object] = {}
    try:
        rootstock_repo = args.rootstock_repo.resolve()
        ensure_directory(rootstock_repo, "--rootstock-repo")
        ensure_git_repository(rootstock_repo, args.verbose)

        main_status = compute_main_status(rootstock_repo, args.verbose)
        contributors = compute_contributor_status(rootstock_repo, args.verbose)
        reports = read_reports_status(rootstock_repo)
        health = compute_health(main_status, contributors, reports)

        print_human_dashboard(main_status, contributors, reports, health)

        payload = {
            "status": "ok",
            "timestamp": datetime.now(UTC).isoformat(),
            "main": main_status,
            "contributors": contributors,
            "reports": reports,
            "health": health,
        }
        emit_json(payload)
        return EXIT_SUCCESS
    except Exception as exc:  # noqa: BLE001
        return fail(str(exc), payload if payload else None)


if __name__ == "__main__":
    raise SystemExit(main())
