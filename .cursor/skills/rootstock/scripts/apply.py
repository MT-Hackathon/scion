#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

"""Apply approved Rootstock curation decisions to canonical main."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys

EXIT_SUCCESS = 0
EXIT_ERROR = 1

BASE_BRANCH = "main"
CURSOR_DIRNAME = ".cursor"
DATE_FORMAT = "%Y-%m-%d"
GIT_TIMEOUT_SECONDS = 120

RECOMMEND_ACCEPT = "accept"
RECOMMEND_MOVE = "move"
RECOMMEND_PRUNE = "prune"
RECOMMEND_REJECT = "reject"
RECOMMEND_REVISE = "revise"

ACTIONABLE_RECOMMENDATIONS = {RECOMMEND_ACCEPT, RECOMMEND_MOVE, RECOMMEND_PRUNE}
SKIPPED_RECOMMENDATIONS = {RECOMMEND_REJECT, RECOMMEND_REVISE}


@dataclass(frozen=True)
class CurationDecision:
    """Single curated decision from report JSON."""

    change_id: str
    artifact_path: PurePosixPath
    recommendation: str
    target_location: PurePosixPath | None


def emit_json(payload: dict[str, object]) -> None:
    """Emit machine-readable JSON payload to stdout."""
    print(json.dumps(payload, indent=2))


def log(message: str) -> None:
    """Emit human-readable status to stderr."""
    sys.stderr.write(f"{message}\n")


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        prog="apply.py",
        description=(
            "Apply approved curation recommendations to canonical main by copying "
            "approved artifacts from a contributor branch."
        ),
    )
    parser.add_argument(
        "--report",
        type=Path,
        required=True,
        help="Path to curation JSON report.",
    )
    parser.add_argument(
        "--rootstock-repo",
        type=Path,
        required=True,
        help="Path to local Rootstock repository clone.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview curated file operations without writing, staging, or committing.",
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


def normalize_artifact_path(path_text: str, field_name: str) -> PurePosixPath:
    """Normalize report path to repo-relative .cursor/* path."""
    raw = path_text.strip()
    if raw == "":
        raise ValueError(f"{field_name} cannot be blank.")
    path = PurePosixPath(raw)
    if path.is_absolute():
        raise ValueError(f"{field_name} must be relative, got absolute path: {raw}")
    if len(path.parts) > 0 and path.parts[0].endswith(":"):
        raise ValueError(f"{field_name} must be POSIX-style relative path, got: {raw}")
    if ".." in path.parts:
        raise ValueError(f"{field_name} cannot traverse parent directories: {raw}")
    if path.parts and path.parts[0] == CURSOR_DIRNAME:
        normalized = path
    else:
        normalized = PurePosixPath(CURSOR_DIRNAME) / path
    if len(normalized.parts) < 2:
        raise ValueError(f"{field_name} must point to a file under .cursor/: {raw}")
    if normalized.parts[0] != CURSOR_DIRNAME:
        raise ValueError(f"{field_name} must be under .cursor/: {raw}")
    return normalized


def ensure_report_metadata(report_data: dict[str, object]) -> tuple[str, str, str]:
    """Validate required report metadata fields."""
    metadata = report_data.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError("Report is missing required 'metadata' object.")
    contributor = str(metadata.get("contributor", "")).strip()
    branch = str(metadata.get("branch", "")).strip()
    base = str(metadata.get("base", "")).strip()
    if contributor == "":
        raise ValueError("Report metadata.contributor is required.")
    if branch == "":
        raise ValueError("Report metadata.branch is required.")
    if base == "":
        raise ValueError("Report metadata.base is required.")
    if base != BASE_BRANCH:
        raise ValueError(
            f"Report metadata.base must be '{BASE_BRANCH}' for apply workflow, got: {base}"
        )
    return contributor, branch, base


def parse_decisions(report_data: dict[str, object]) -> list[CurationDecision]:
    """Parse and validate report decision records."""
    raw_decisions = report_data.get("decisions")
    if not isinstance(raw_decisions, list):
        raise ValueError("Report is missing required 'decisions' array.")
    decisions: list[CurationDecision] = []
    for index, raw_item in enumerate(raw_decisions):
        if not isinstance(raw_item, dict):
            raise ValueError(f"Decision at index {index} is not an object.")
        change_id = str(raw_item.get("change_id", "")).strip()
        recommendation = str(raw_item.get("recommendation", "")).strip().lower()
        artifact_path_raw = str(raw_item.get("artifact_path", "")).strip()
        if change_id == "":
            raise ValueError(f"Decision at index {index} is missing change_id.")
        if recommendation == "":
            raise ValueError(f"Decision {change_id} is missing recommendation.")
        if artifact_path_raw == "":
            raise ValueError(f"Decision {change_id} is missing artifact_path.")
        artifact_path = normalize_artifact_path(artifact_path_raw, "artifact_path")
        target_location: PurePosixPath | None = None
        if recommendation == RECOMMEND_MOVE:
            target_raw = raw_item.get("target_location")
            if not isinstance(target_raw, str) or target_raw.strip() == "":
                raise ValueError(
                    f"Decision {change_id} recommendation=move requires target_location."
                )
            target_location = normalize_artifact_path(target_raw, "target_location")
        decisions.append(
            CurationDecision(
                change_id=change_id,
                artifact_path=artifact_path,
                recommendation=recommendation,
                target_location=target_location,
            )
        )
    return decisions


def read_report(report_path: Path) -> tuple[dict[str, object], str, str, str, list[CurationDecision]]:
    """Load and validate report envelope."""
    try:
        report_data = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON report: {report_path}: {exc}") from exc
    if not isinstance(report_data, dict):
        raise ValueError("Report root must be a JSON object.")
    contributor, branch, base = ensure_report_metadata(report_data)
    decisions = parse_decisions(report_data)
    return report_data, contributor, branch, base, decisions


def extract_git_error(process: subprocess.CompletedProcess[str]) -> str:
    """Extract concise git error message from failed process."""
    stderr = process.stderr.strip()
    stdout = process.stdout.strip()
    details = stderr if stderr != "" else stdout
    if details == "":
        return "git command failed without output"
    return details


def read_branch_file(
    repo_path: Path,
    source_branch: str,
    source_path: PurePosixPath,
    verbose: bool,
) -> str:
    """Read file content from source branch using git show."""
    completed = run_git(
        repo_path=repo_path,
        args=["show", f"{source_branch}:{source_path.as_posix()}"],
        verbose=verbose,
    )
    return completed.stdout


def path_exists_in_branch(
    repo_path: Path,
    branch: str,
    relative_path: PurePosixPath,
    verbose: bool,
) -> bool:
    """Check whether file exists at branch:path."""
    completed = run_git(
        repo_path=repo_path,
        args=["cat-file", "-e", f"{branch}:{relative_path.as_posix()}"],
        verbose=verbose,
        allow_failure=True,
    )
    if completed.returncode == 0:
        return True
    if completed.returncode == 1:
        return False
    raise RuntimeError(
        f"Unable to check path existence for {branch}:{relative_path.as_posix()}: "
        f"{extract_git_error(completed)}"
    )


def write_repo_file(repo_path: Path, relative_path: PurePosixPath, content: str, dry_run: bool) -> None:
    """Write file content to working tree path."""
    if dry_run:
        return
    target = repo_path / Path(relative_path.as_posix())
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def delete_repo_file(repo_path: Path, relative_path: PurePosixPath, dry_run: bool) -> bool:
    """Delete file from working tree if present."""
    target = repo_path / Path(relative_path.as_posix())
    if not target.exists():
        return False
    if target.is_dir():
        raise ValueError(f"Expected file path but found directory: {relative_path.as_posix()}")
    if not dry_run:
        target.unlink()
    return True


def stage_paths(repo_path: Path, paths: set[PurePosixPath], verbose: bool) -> None:
    """Stage changed files by explicit path list."""
    if not paths:
        return
    ordered = sorted(path.as_posix() for path in paths)
    run_git(repo_path=repo_path, args=["add", "--", *ordered], verbose=verbose)


def commit_if_staged(
    repo_path: Path,
    contributor: str,
    accepted_count: int,
    moved_count: int,
    pruned_count: int,
    verbose: bool,
) -> tuple[bool, str | None, str | None]:
    """Commit staged changes if any exist."""
    staged = run_git(
        repo_path=repo_path,
        args=["diff", "--cached", "--quiet"],
        verbose=verbose,
        allow_failure=True,
    )
    if staged.returncode == 0:
        return False, None, None
    if staged.returncode != 1:
        raise RuntimeError("Unable to determine staged diff state.")

    iso_date = datetime.now(UTC).strftime(DATE_FORMAT)
    title = f"apply: curated changes from {contributor} {iso_date}"
    body = (
        f"Accepted: {accepted_count}\n"
        f"Moved: {moved_count}\n"
        f"Pruned: {pruned_count}"
    )
    run_git(
        repo_path=repo_path,
        args=["commit", "-m", title, "-m", body],
        verbose=verbose,
    )
    commit_hash = run_git(
        repo_path=repo_path,
        args=["rev-parse", "--short", "HEAD"],
        verbose=verbose,
    ).stdout.strip()
    return True, title, commit_hash


def print_human_summary(
    contributor: str,
    source_branch: str,
    accepted_count: int,
    moved_count: int,
    pruned_count: int,
    skipped_count: int,
    dry_run: bool,
    committed: bool,
    commit_hash: str | None,
) -> None:
    """Emit concise human summary to stderr."""
    mode = "DRY RUN" if dry_run else "APPLIED"
    log(f"[{mode}] contributor={contributor} source_branch={source_branch} base={BASE_BRANCH}")
    log(f"Accepted: {accepted_count}")
    log(f"Moved: {moved_count}")
    log(f"Pruned: {pruned_count}")
    log(f"Skipped: {skipped_count}")
    if dry_run:
        log("Git stage/commit operations skipped due to --dry-run.")
        return
    if committed:
        if commit_hash is None:
            log("Commit created.")
            return
        log(f"Commit created: {commit_hash}")
        return
    log("No staged changes from actionable recommendations. Commit skipped.")


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    args = parse_args(sys.argv[1:] if argv is None else argv)
    payload: dict[str, object] = {}
    try:
        report_path = args.report.resolve()
        rootstock_repo = args.rootstock_repo.resolve()

        ensure_file(report_path, "--report")
        ensure_directory(rootstock_repo, "--rootstock-repo")
        ensure_git_repository(rootstock_repo, args.verbose)
        if not branch_exists(rootstock_repo, BASE_BRANCH, args.verbose):
            raise ValueError("Local base branch 'main' does not exist in rootstock repo.")

        _, contributor, source_branch, _, decisions = read_report(report_path)
        if not branch_exists(rootstock_repo, source_branch, args.verbose):
            raise ValueError(f"Contributor branch in report does not exist locally: {source_branch}")

        ensure_branch_checked_out(rootstock_repo, BASE_BRANCH, args.verbose)

        accepted_count = 0
        moved_count = 0
        pruned_count = 0
        skipped_count = 0
        staged_paths: set[PurePosixPath] = set()
        applied: list[dict[str, object]] = []
        skipped: list[dict[str, object]] = []

        for decision in decisions:
            recommendation = decision.recommendation
            artifact = decision.artifact_path
            if recommendation in SKIPPED_RECOMMENDATIONS:
                skipped_count += 1
                skipped.append(
                    {
                        "change_id": decision.change_id,
                        "recommendation": recommendation,
                        "artifact_path": artifact.as_posix(),
                        "reason": "non-actionable recommendation",
                    }
                )
                continue
            if recommendation not in ACTIONABLE_RECOMMENDATIONS:
                skipped_count += 1
                skipped.append(
                    {
                        "change_id": decision.change_id,
                        "recommendation": recommendation,
                        "artifact_path": artifact.as_posix(),
                        "reason": "unknown recommendation",
                    }
                )
                continue

            if recommendation == RECOMMEND_ACCEPT:
                content = read_branch_file(rootstock_repo, source_branch, artifact, args.verbose)
                write_repo_file(rootstock_repo, artifact, content, args.dry_run)
                staged_paths.add(artifact)
                accepted_count += 1
                applied.append(
                    {
                        "change_id": decision.change_id,
                        "recommendation": recommendation,
                        "source_branch": source_branch,
                        "source_path": artifact.as_posix(),
                        "target_path": artifact.as_posix(),
                        "operation": "copy",
                    }
                )
                continue

            if recommendation == RECOMMEND_MOVE:
                if decision.target_location is None:
                    raise ValueError(
                        f"Decision {decision.change_id} recommendation=move requires target_location."
                    )
                target = decision.target_location
                content = read_branch_file(rootstock_repo, source_branch, artifact, args.verbose)
                write_repo_file(rootstock_repo, target, content, args.dry_run)
                staged_paths.add(target)

                deleted_original = False
                if artifact != target and path_exists_in_branch(
                    rootstock_repo, BASE_BRANCH, artifact, args.verbose
                ):
                    deleted_original = delete_repo_file(rootstock_repo, artifact, args.dry_run)
                    staged_paths.add(artifact)

                moved_count += 1
                applied.append(
                    {
                        "change_id": decision.change_id,
                        "recommendation": recommendation,
                        "source_branch": source_branch,
                        "source_path": artifact.as_posix(),
                        "target_path": target.as_posix(),
                        "operation": "move",
                        "deleted_original_on_main": deleted_original,
                    }
                )
                continue

            if recommendation == RECOMMEND_PRUNE:
                existed_on_main = path_exists_in_branch(rootstock_repo, BASE_BRANCH, artifact, args.verbose)
                deleted = False
                if existed_on_main:
                    deleted = delete_repo_file(rootstock_repo, artifact, args.dry_run)
                    staged_paths.add(artifact)
                pruned_count += 1
                applied.append(
                    {
                        "change_id": decision.change_id,
                        "recommendation": recommendation,
                        "artifact_path": artifact.as_posix(),
                        "operation": "prune",
                        "existed_on_main": existed_on_main,
                        "deleted": deleted,
                    }
                )
                continue

        committed = False
        commit_message: str | None = None
        commit_hash: str | None = None
        if not args.dry_run:
            stage_paths(rootstock_repo, staged_paths, args.verbose)
            committed, commit_message, commit_hash = commit_if_staged(
                repo_path=rootstock_repo,
                contributor=contributor,
                accepted_count=accepted_count,
                moved_count=moved_count,
                pruned_count=pruned_count,
                verbose=args.verbose,
            )

        print_human_summary(
            contributor=contributor,
            source_branch=source_branch,
            accepted_count=accepted_count,
            moved_count=moved_count,
            pruned_count=pruned_count,
            skipped_count=skipped_count,
            dry_run=args.dry_run,
            committed=committed,
            commit_hash=commit_hash,
        )

        payload = {
            "status": "ok",
            "report": str(report_path),
            "metadata": {
                "contributor": contributor,
                "branch": source_branch,
                "base": BASE_BRANCH,
            },
            "dry_run": args.dry_run,
            "counts": {
                "accepted": accepted_count,
                "moved": moved_count,
                "pruned": pruned_count,
                "skipped": skipped_count,
                "actionable_applied": len(applied),
            },
            "applied_decisions": applied,
            "skipped_decisions": skipped,
            "committed": committed,
        }
        if commit_message is not None:
            payload["commit_message"] = commit_message
        if commit_hash is not None:
            payload["commit_hash"] = commit_hash
        emit_json(payload)
        return EXIT_SUCCESS
    except Exception as exc:  # noqa: BLE001
        return fail(str(exc), payload if payload else None)


if __name__ == "__main__":
    raise SystemExit(main())
