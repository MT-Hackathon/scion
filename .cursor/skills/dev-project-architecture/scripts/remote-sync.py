#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Configure and verify multi-remote git synchronization."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_USAGE = 2
DEFAULT_TIMEOUT_SECONDS = 20


@dataclass(frozen=True)
class CommandResult:
    """Result wrapper for subprocess calls."""

    returncode: int
    stdout: str
    stderr: str


def run_command(
    args: Sequence[str],
    cwd: Path,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> CommandResult:
    """Run a subprocess command with explicit timeout and cwd."""
    completed = subprocess.run(
        list(args),
        cwd=str(cwd),
        timeout=timeout,
        capture_output=True,
        text=True,
        check=False,
    )
    return CommandResult(
        returncode=completed.returncode,
        stdout=completed.stdout.strip(),
        stderr=completed.stderr.strip(),
    )


def ensure_git_repo(repo_dir: Path) -> bool:
    """Validate that cwd is inside a git repository."""
    result = run_command(["git", "rev-parse", "--is-inside-work-tree"], cwd=repo_dir)
    return result.returncode == 0 and result.stdout == "true"


def current_branch(repo_dir: Path) -> str | None:
    """Return current git branch or None when detached/unavailable."""
    result = run_command(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=repo_dir,
    )
    if result.returncode != 0:
        return None
    if result.stdout == "HEAD":
        return None
    return result.stdout


def remote_exists(remote_name: str, repo_dir: Path) -> bool:
    """Check whether a git remote exists."""
    result = run_command(["git", "remote", "get-url", remote_name], cwd=repo_dir)
    return result.returncode == 0


def set_remote(remote_name: str, remote_url: str, repo_dir: Path) -> CommandResult:
    """Create or update a git remote URL."""
    if remote_exists(remote_name, repo_dir):
        return run_command(
            ["git", "remote", "set-url", remote_name, remote_url],
            cwd=repo_dir,
        )
    return run_command(
        ["git", "remote", "add", remote_name, remote_url],
        cwd=repo_dir,
    )


def remote_urls(repo_name: str) -> dict[str, str]:
    """Build remote URLs from repo name and environment configuration."""
    cdo_group = os.environ.get("CDO_GITLAB_GROUP", "cdo-office").strip()
    github_org = os.environ.get("GITHUB_ORG", "MT-Hackathon").strip()
    state_path = os.environ.get("STATE_GITLAB_PATH", "").strip()

    remotes: dict[str, str] = {
        "origin": f"git@gitlab.com:{cdo_group}/{repo_name}.git",
        "github": f"git@github.com:{github_org}/{repo_name}.git",
    }
    if state_path:
        base = state_path.rstrip("/")
        remotes["state"] = f"{base}/{repo_name}.git"
    return remotes


def parse_remotes(value: str) -> list[str]:
    """Parse comma-separated remote names."""
    return [item.strip() for item in value.split(",") if item.strip()]


def handle_configure(args: argparse.Namespace, repo_dir: Path) -> int:
    """Configure origin/github/state remotes based on environment."""
    remotes = remote_urls(args.repo_name)
    for name, url in remotes.items():
        result = set_remote(name, url, repo_dir)
        if result.returncode != 0:
            print(f"[error] failed to configure {name}: {result.stderr or result.stdout}")
            return EXIT_ERROR
        print(f"[ok] {name} -> {url}")

    if "state" not in remotes:
        print(
            "[warn] STATE_GITLAB_PATH not set; skipping state remote "
            "(set env var to enable)."
        )

    listing = run_command(["git", "remote", "-v"], cwd=repo_dir)
    if listing.returncode == 0 and listing.stdout:
        print("\nCurrent remotes:")
        print(listing.stdout)
    return EXIT_SUCCESS


def handle_push(args: argparse.Namespace, repo_dir: Path) -> int:
    """Push branch to selected remotes and report per-remote outcomes."""
    selected_remotes = parse_remotes(args.remotes)
    branch = args.branch or current_branch(repo_dir)
    if not branch:
        print("[error] unable to resolve branch; provide --branch explicitly.")
        return EXIT_ERROR

    exit_code = EXIT_SUCCESS
    for remote in selected_remotes:
        if not remote_exists(remote, repo_dir):
            print(f"[error] remote '{remote}' does not exist.")
            exit_code = EXIT_ERROR
            continue

        result = run_command(
            ["git", "push", remote, branch],
            cwd=repo_dir,
            timeout=args.push_timeout,
        )
        if result.returncode == 0:
            print(f"[ok] pushed {branch} -> {remote}")
        else:
            print(f"[error] push failed for {remote}: {result.stderr or result.stdout}")
            exit_code = EXIT_ERROR
    return exit_code


def ahead_behind(local_ref: str, remote_ref: str, repo_dir: Path) -> tuple[str, str]:
    """Compute ahead/behind counts from local branch to remote branch."""
    result = run_command(
        ["git", "rev-list", "--left-right", "--count", f"{local_ref}...{remote_ref}"],
        cwd=repo_dir,
    )
    if result.returncode != 0 or not result.stdout:
        return ("?", "?")
    parts = result.stdout.split()
    if len(parts) != 2:
        return ("?", "?")
    return (parts[0], parts[1])


def tracking_ref(repo_dir: Path) -> str | None:
    """Return upstream tracking ref for current branch, if configured."""
    result = run_command(
        ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
        cwd=repo_dir,
    )
    if result.returncode != 0 or not result.stdout:
        return None
    return result.stdout


def remote_branch_exists(remote: str, branch: str, repo_dir: Path) -> bool:
    """Check whether remote branch exists."""
    result = run_command(
        ["git", "show-ref", "--verify", "--quiet", f"refs/remotes/{remote}/{branch}"],
        cwd=repo_dir,
    )
    return result.returncode == 0


def handle_status(args: argparse.Namespace, repo_dir: Path) -> int:
    """Show connectivity, tracking, and ahead/behind for remotes."""
    branch = args.branch or current_branch(repo_dir)
    if not branch:
        print("[error] unable to resolve branch; provide --branch explicitly.")
        return EXIT_ERROR

    remotes = parse_remotes(args.remotes)
    track = tracking_ref(repo_dir)
    print(f"Branch: {branch}")
    print(f"Tracking: {track or '(none)'}")
    print("")

    overall = EXIT_SUCCESS
    for remote in remotes:
        if not remote_exists(remote, repo_dir):
            print(f"{remote}: [missing]")
            overall = EXIT_ERROR
            continue

        fetch_result = run_command(
            ["git", "fetch", "--dry-run", remote],
            cwd=repo_dir,
            timeout=args.fetch_timeout,
        )
        connectivity = "ok" if fetch_result.returncode == 0 else "unreachable"

        remote_ref = f"{remote}/{branch}"
        if remote_branch_exists(remote, branch, repo_dir):
            ahead, behind = ahead_behind(branch, remote_ref, repo_dir)
        else:
            ahead, behind = ("?", "?")

        print(
            f"{remote}: connectivity={connectivity}, "
            f"ahead={ahead}, behind={behind}, remote_ref={remote_ref}"
        )
        if fetch_result.returncode != 0:
            details = fetch_result.stderr or fetch_result.stdout
            if details:
                print(f"  details: {details}")
            overall = EXIT_ERROR
    return overall


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(
        prog="remote-sync.py",
        description="Configure, push, and inspect git remotes for sync workflows.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    configure = subparsers.add_parser(
        "configure",
        help="Configure origin/github/state remotes from environment bases.",
    )
    configure.add_argument("--repo-name", required=True, help="Repository name.")

    push = subparsers.add_parser(
        "push",
        help="Push branch to selected remotes.",
    )
    push.add_argument(
        "--remotes",
        default="origin,github",
        help="Comma-separated remote names (default: origin,github).",
    )
    push.add_argument(
        "--branch",
        help="Branch to push (default: current branch).",
    )
    push.add_argument(
        "--push-timeout",
        type=int,
        default=60,
        help="Timeout seconds per git push (default: 60).",
    )

    status = subparsers.add_parser(
        "status",
        help="Check remote connectivity and ahead/behind counts.",
    )
    status.add_argument(
        "--remotes",
        default="origin,github,state",
        help="Comma-separated remote names (default: origin,github,state).",
    )
    status.add_argument(
        "--branch",
        help="Branch to inspect (default: current branch).",
    )
    status.add_argument(
        "--fetch-timeout",
        type=int,
        default=30,
        help="Timeout seconds per dry-run fetch (default: 30).",
    )
    return parser


def main() -> int:
    """Script entrypoint."""
    parser = build_parser()
    try:
        args = parser.parse_args()
    except SystemExit as exc:
        code = int(exc.code) if isinstance(exc.code, int) else EXIT_USAGE
        return EXIT_USAGE if code != 0 else EXIT_SUCCESS

    repo_dir = Path.cwd().resolve()
    if not ensure_git_repo(repo_dir):
        print("[error] current directory is not a git repository.")
        return EXIT_ERROR

    try:
        if args.command == "configure":
            return handle_configure(args, repo_dir)
        if args.command == "push":
            return handle_push(args, repo_dir)
        if args.command == "status":
            return handle_status(args, repo_dir)
    except subprocess.TimeoutExpired:
        print("[error] command timed out.")
        return EXIT_ERROR
    except OSError as exc:
        print(f"[error] OS failure: {exc}")
        return EXIT_ERROR

    print("[error] unknown command.")
    return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
