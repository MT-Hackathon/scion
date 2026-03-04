#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

"""Rebase contributor branches on canonical main."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import json
from pathlib import Path
import re
import subprocess
import sys

EXIT_SUCCESS = 0
EXIT_ERROR = 1

BASE_BRANCH = "main"
CONTRIBUTOR_PREFIX = "contributor/"
CONTRIBUTOR_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
GIT_TIMEOUT_SECONDS = 120

STATUS_SUCCESS = "success"
STATUS_FAILED = "failed"
STATUS_SKIPPED = "skipped"
STATUS_DRY_RUN = "dry-run"


@dataclass(frozen=True)
class BranchPlan:
    """Contributor branch rebase plan item."""

    branch: str
    contributor: str
    main_is_ancestor: bool


def emit_json(payload: dict[str, object]) -> None:
    """Emit machine-readable JSON payload to stdout."""
    print(json.dumps(payload, indent=2))


def log(message: str) -> None:
    """Emit human-readable status to stderr."""
    sys.stderr.write(f"{message}\n")


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        prog="rebase.py",
        description=(
            "Rebase contributor/* branches onto canonical main, with per-branch "
            "status tracking and safe force-with-lease push."
        ),
    )
    parser.add_argument(
        "--rootstock-repo",
        type=Path,
        required=True,
        help="Path to local Rootstock repository clone.",
    )
    parser.add_argument(
        "--contributor",
        help="Contributor name to process (resolved to contributor/{name}).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview rebase operations without changing branches or pushing.",
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


def parse_branch_to_contributor(branch: str) -> str:
    """Extract contributor name from contributor/{name} branch."""
    if not branch.startswith(CONTRIBUTOR_PREFIX):
        raise ValueError(f"Branch does not follow contributor/* pattern: {branch}")
    contributor = branch[len(CONTRIBUTOR_PREFIX) :].strip()
    if contributor == "":
        raise ValueError(f"Contributor branch has empty suffix: {branch}")
    return contributor


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


def branch_exists(repo_path: Path, branch: str, verbose: bool) -> bool:
    """Check whether a local branch exists."""
    result = run_git(
        repo_path=repo_path,
        args=["show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
        verbose=verbose,
        allow_failure=True,
    )
    return result.returncode == 0


def ensure_branch_checked_out(repo_path: Path, branch: str, verbose: bool) -> None:
    """Checkout branch, validating local existence."""
    if not branch_exists(repo_path, branch, verbose):
        raise ValueError(f"Branch does not exist locally: {branch}")
    run_git(repo_path=repo_path, args=["checkout", branch], verbose=verbose)


def list_contributor_branches(repo_path: Path, verbose: bool) -> list[str]:
    """List all local contributor/* branches."""
    completed = run_git(
        repo_path=repo_path,
        args=["for-each-ref", "--format=%(refname:short)", "refs/heads/contributor/"],
        verbose=verbose,
    )
    branches = [line.strip() for line in completed.stdout.splitlines() if line.strip() != ""]
    return sorted(branches)


def extract_git_error(process: subprocess.CompletedProcess[str]) -> str:
    """Extract concise git error message from failed process."""
    stderr = process.stderr.strip()
    stdout = process.stdout.strip()
    details = stderr if stderr != "" else stdout
    if details == "":
        return "git command failed without output"
    return details


def get_current_branch(repo_path: Path, verbose: bool) -> str:
    """Get current branch name."""
    completed = run_git(
        repo_path=repo_path,
        args=["rev-parse", "--abbrev-ref", "HEAD"],
        verbose=verbose,
    )
    branch = completed.stdout.strip()
    if branch == "":
        raise RuntimeError("Unable to determine current branch.")
    return branch


def list_stash_entries(repo_path: Path, verbose: bool) -> list[str]:
    """List current stash entries for warning output."""
    completed = run_git(repo_path=repo_path, args=["stash", "list"], verbose=verbose)
    return [line.strip() for line in completed.stdout.splitlines() if line.strip() != ""]


def is_ancestor(repo_path: Path, ancestor: str, descendant: str, verbose: bool) -> bool:
    """Return whether ancestor commit is in descendant history."""
    completed = run_git(
        repo_path=repo_path,
        args=["merge-base", "--is-ancestor", ancestor, descendant],
        verbose=verbose,
        allow_failure=True,
    )
    if completed.returncode == 0:
        return True
    if completed.returncode == 1:
        return False
    raise RuntimeError(
        f"Unable to evaluate ancestry {ancestor} -> {descendant}: {extract_git_error(completed)}"
    )


def build_rebase_plan(repo_path: Path, branches: list[str], verbose: bool) -> list[BranchPlan]:
    """Build per-branch safety plan records."""
    plans: list[BranchPlan] = []
    for branch in branches:
        contributor = parse_branch_to_contributor(branch)
        plans.append(
            BranchPlan(
                branch=branch,
                contributor=contributor,
                main_is_ancestor=is_ancestor(repo_path, BASE_BRANCH, branch, verbose),
            )
        )
    return plans


def rebase_branch(repo_path: Path, branch: str, verbose: bool) -> tuple[bool, str | None]:
    """Rebase contributor branch onto main."""
    ensure_branch_checked_out(repo_path, branch, verbose)
    rebase = run_git(
        repo_path=repo_path,
        args=["rebase", BASE_BRANCH],
        verbose=verbose,
        allow_failure=True,
    )
    if rebase.returncode == 0:
        return True, None
    details = extract_git_error(rebase)
    run_git(
        repo_path=repo_path,
        args=["rebase", "--abort"],
        verbose=verbose,
        allow_failure=True,
    )
    return False, details


def push_branch(repo_path: Path, branch: str, verbose: bool) -> tuple[bool, str | None]:
    """Push rebased branch with force-with-lease."""
    push = run_git(
        repo_path=repo_path,
        args=["push", "--force-with-lease", "origin", branch],
        verbose=verbose,
        allow_failure=True,
    )
    if push.returncode == 0:
        return True, None
    return False, extract_git_error(push)


def print_human_summary(
    branch_results: list[dict[str, object]],
    dry_run: bool,
    stash_count: int,
) -> None:
    """Emit concise per-branch summary to stderr."""
    mode = "DRY RUN" if dry_run else "APPLIED"
    log(f"[{mode}] base={BASE_BRANCH} stash_entries={stash_count}")
    for result in branch_results:
        branch = str(result["branch"])
        status = str(result["status"])
        reason = str(result.get("reason", "")).strip()
        if reason == "":
            log(f"- {branch}: {status}")
            continue
        log(f"- {branch}: {status} ({reason})")
    counts = Counter(str(item["status"]) for item in branch_results)
    log(
        "Totals: "
        f"success={counts.get(STATUS_SUCCESS, 0)} "
        f"failed={counts.get(STATUS_FAILED, 0)} "
        f"skipped={counts.get(STATUS_SKIPPED, 0)} "
        f"dry-run={counts.get(STATUS_DRY_RUN, 0)}"
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    args = parse_args(sys.argv[1:] if argv is None else argv)
    payload: dict[str, object] = {}
    rootstock_repo = args.rootstock_repo.resolve()
    try:
        ensure_directory(rootstock_repo, "--rootstock-repo")
        ensure_git_repository(rootstock_repo, args.verbose)
        if not branch_exists(rootstock_repo, BASE_BRANCH, args.verbose):
            raise ValueError("Local base branch 'main' does not exist in rootstock repo.")

        branches: list[str]
        if args.contributor is not None:
            contributor = validate_contributor_name(args.contributor)
            branch = f"{CONTRIBUTOR_PREFIX}{contributor}"
            if not branch_exists(rootstock_repo, branch, args.verbose):
                raise ValueError(f"Contributor branch does not exist locally: {branch}")
            branches = [branch]
        else:
            branches = list_contributor_branches(rootstock_repo, args.verbose)
            if not branches:
                raise ValueError("No local contributor/* branches found.")

        stash_entries = list_stash_entries(rootstock_repo, args.verbose)
        if stash_entries:
            log(
                f"WARNING: Detected {len(stash_entries)} stash entr"
                f"{'y' if len(stash_entries) == 1 else 'ies'}. Continue with caution."
            )

        plans = build_rebase_plan(rootstock_repo, branches, args.verbose)
        results: list[dict[str, object]] = []

        for plan in plans:
            if plan.main_is_ancestor:
                results.append(
                    {
                        "branch": plan.branch,
                        "contributor": plan.contributor,
                        "status": STATUS_SKIPPED,
                        "reason": "main already ancestor",
                        "main_is_ancestor": True,
                    }
                )
                continue

            if args.dry_run:
                results.append(
                    {
                        "branch": plan.branch,
                        "contributor": plan.contributor,
                        "status": STATUS_DRY_RUN,
                        "reason": "would rebase onto main and push --force-with-lease",
                        "main_is_ancestor": False,
                    }
                )
                continue

            success, error = rebase_branch(rootstock_repo, plan.branch, args.verbose)
            if not success:
                results.append(
                    {
                        "branch": plan.branch,
                        "contributor": plan.contributor,
                        "status": STATUS_FAILED,
                        "reason": f"rebase failed: {error}",
                        "main_is_ancestor": False,
                    }
                )
                continue

            pushed, push_error = push_branch(rootstock_repo, plan.branch, args.verbose)
            if not pushed:
                results.append(
                    {
                        "branch": plan.branch,
                        "contributor": plan.contributor,
                        "status": STATUS_FAILED,
                        "reason": f"push failed: {push_error}",
                        "main_is_ancestor": False,
                    }
                )
                continue

            results.append(
                {
                    "branch": plan.branch,
                    "contributor": plan.contributor,
                    "status": STATUS_SUCCESS,
                    "main_is_ancestor": False,
                }
            )

        ensure_branch_checked_out(rootstock_repo, BASE_BRANCH, args.verbose)
        print_human_summary(results, args.dry_run, len(stash_entries))

        status_counts = Counter(str(item["status"]) for item in results)
        payload = {
            "status": "ok",
            "base": BASE_BRANCH,
            "dry_run": args.dry_run,
            "branch_count": len(results),
            "stash_count": len(stash_entries),
            "counts": {
                STATUS_SUCCESS: status_counts.get(STATUS_SUCCESS, 0),
                STATUS_FAILED: status_counts.get(STATUS_FAILED, 0),
                STATUS_SKIPPED: status_counts.get(STATUS_SKIPPED, 0),
                STATUS_DRY_RUN: status_counts.get(STATUS_DRY_RUN, 0),
            },
            "results": results,
        }
        emit_json(payload)
        return EXIT_SUCCESS
    except Exception as exc:  # noqa: BLE001
        try:
            if branch_exists(rootstock_repo, BASE_BRANCH, args.verbose):
                ensure_branch_checked_out(rootstock_repo, BASE_BRANCH, args.verbose)
        except Exception:  # noqa: BLE001
            pass
        return fail(str(exc), payload if payload else None)


if __name__ == "__main__":
    raise SystemExit(main())
