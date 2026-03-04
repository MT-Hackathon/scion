#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "python-dotenv>=1.0",
#   "httpx>=0.27",
# ]
# ///
from __future__ import annotations

import argparse
from collections.abc import Callable
from typing import Any, Sequence

from _core import (
    add_common_args,
    add_provider_args,
    emit_error,
    emit_markdown,
    emit_text,
    get_provider,
    truncate,
    validate_provider_args,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def ensure_project(provider: Any) -> str:
    project = getattr(provider, "project", None)
    if not project:
        emit_error("Project must be provided via --project or environment.")
    return project


def ensure_ok_dict(result: Any, context: str) -> dict[str, Any]:
    if result.get("ok") and isinstance(result.get("data"), dict):
        return result["data"]
    status = result.get("status_code")
    detail = result.get("error") or "Unknown error"
    emit_error(f"{context} failed (HTTP {status}): {detail}")
    raise AssertionError("unreachable")


def ensure_ok_list(result: Any, context: str) -> list[dict[str, Any]]:
    if result.get("ok") and isinstance(result.get("data"), list):
        return result["data"]
    status = result.get("status_code")
    detail = result.get("error") or "Unknown error"
    emit_error(f"{context} failed (HTTP {status}): {detail}")
    raise AssertionError("unreachable")


def ensure_gitlab_provider(name: str) -> None:
    if name == "github":
        emit_error("git-pipeline supports gitlab/state providers only.")


def parse_variables(entries: list[str] | None) -> list[dict[str, str]]:
    if not entries:
        return []
    variables: list[dict[str, str]] = []
    for entry in entries:
        if "=" not in entry:
            emit_error(f"Invalid variable '{entry}'. Use KEY=VALUE.")
        key, value = entry.split("=", 1)
        key = key.strip()
        if not key:
            emit_error("Variable key must be non-empty.")
        variables.append({"key": key, "value": value})
    return variables


def pipeline_url(base: str, project: str, pipeline_id: int) -> str:
    host = "gitlab.com" if base.endswith("gitlab.com/api/v4") else "git.mt.gov"
    return f"https://{host}/{project}/-/pipelines/{pipeline_id}"


# ---------------------------------------------------------------------------
# Operations (GitLab/State)
# ---------------------------------------------------------------------------


def do_trigger(provider: Any, ref: str, variables: list[dict[str, str]], dry_run: bool) -> None:
    if dry_run:
        emit_text(["[dry-run] trigger pipeline", f"ref={ref}", f"vars={variables}"])
        return
    project = ensure_project(provider)
    payload: dict[str, Any] = {"ref": ref}
    if variables:
        payload["variables"] = variables
    result = provider.request("POST", "/projects/{project}/pipeline", json=payload)
    data = ensure_ok_dict(result, "Trigger pipeline")
    url = data.get("web_url") or pipeline_url(str(provider.base_url), project, data.get("id", 0))
    emit_text([f"Triggered pipeline {data.get('id')} -> {url}"])


def do_cancel(provider: Any, pipeline_id: int, dry_run: bool) -> None:
    if dry_run:
        emit_text([f"[dry-run] cancel pipeline {pipeline_id}"])
        return
    project = ensure_project(provider)
    endpoint = f"/projects/{{project}}/pipelines/{pipeline_id}/cancel"
    result = provider.request("POST", endpoint)
    ensure_ok_dict(result, "Cancel pipeline")
    emit_text([f"Canceled pipeline {pipeline_id}"])


def do_retry(provider: Any, pipeline_id: int, dry_run: bool) -> None:
    if dry_run:
        emit_text([f"[dry-run] retry pipeline {pipeline_id}"])
        return
    project = ensure_project(provider)
    endpoint = f"/projects/{{project}}/pipelines/{pipeline_id}/retry"
    result = provider.request("POST", endpoint)
    ensure_ok_dict(result, "Retry pipeline")
    emit_text([f"Retried pipeline {pipeline_id}"])


def do_list(provider: Any, ref: str | None, status: str | None, limit: int) -> None:
    project = ensure_project(provider)
    params: dict[str, Any] = {"per_page": str(min(limit, 100))}
    if ref:
        params["ref"] = ref
    if status:
        params["status"] = status
    result = provider.request("GET", "/projects/{project}/pipelines", params=params)
    items = ensure_ok_list(result, "List pipelines")[:limit]
    lines = []
    for item in items:
        line = f"{item.get('id')}: [{item.get('status')}] {item.get('ref')} {item.get('sha','')[:8]}"
        url = item.get("web_url") or pipeline_url(str(provider.base_url), project, item.get("id", 0))
        if url:
            line += f" {url}"
        lines.append(line)
    emit_text(lines or ["(no pipelines)"])


def do_jobs(provider: Any, pipeline_id: int) -> None:
    ensure_project(provider)
    endpoint = f"/projects/{{project}}/pipelines/{pipeline_id}/jobs"
    result = provider.request("GET", endpoint, params={"per_page": "100"})
    jobs = ensure_ok_list(result, "List jobs")
    lines = []
    for job in jobs:
        line = f"{job.get('id')}: [{job.get('status')}] {job.get('stage')}/{job.get('name')}"
        if job.get("web_url"):
            line += f" {job['web_url']}"
        lines.append(line)
    emit_text(lines or ["(no jobs)"])


def do_trace(provider: Any, job_id: int) -> None:
    ensure_project(provider)
    endpoint = f"/projects/{{project}}/jobs/{job_id}/trace"
    result = provider.request("GET", endpoint)
    if not result.get("ok"):
        status = result.get("status_code")
        detail = result.get("error") or "Unknown error"
        emit_error(f"Fetch trace failed (HTTP {status}): {detail}")
    data = result.get("data")
    if data is None:
        emit_error("Trace response was empty.")
    if isinstance(data, bytes):
        data = data.decode("utf-8", errors="replace")
    if not isinstance(data, str):
        data = str(data)
    emit_markdown(f"```\n{truncate(data, 8000)}\n```")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage GitLab/State pipelines.")
    add_provider_args(parser)
    add_common_args(parser)

    subs = parser.add_subparsers(dest="command", required=True)

    p_trigger = subs.add_parser("trigger", help="Trigger a new pipeline.")
    p_trigger.add_argument("--ref", required=True, help="Branch or tag to build.")
    p_trigger.add_argument(
        "--variables",
        action="append",
        help="Pipeline variable KEY=VALUE (can repeat).",
    )

    p_cancel = subs.add_parser("cancel", help="Cancel a running pipeline.")
    p_cancel.add_argument("pipeline_id", type=int, help="Pipeline ID.")

    p_retry = subs.add_parser("retry", help="Retry a pipeline.")
    p_retry.add_argument("pipeline_id", type=int, help="Pipeline ID.")

    p_list = subs.add_parser("list", help="List recent pipelines.")
    p_list.add_argument("--ref", help="Filter by ref.")
    p_list.add_argument(
        "--status",
        choices=["running", "pending", "success", "failed", "canceled", "skipped"],
        help="Pipeline status filter.",
    )
    p_list.add_argument("--limit", type=int, default=20, help="Max pipelines to show.")

    p_jobs = subs.add_parser("jobs", help="List jobs for a pipeline.")
    p_jobs.add_argument("pipeline_id", type=int, help="Pipeline ID.")

    p_trace = subs.add_parser("trace", help="Fetch job trace.")
    p_trace.add_argument("job_id", type=int, help="Job ID.")

    return parser


def _cmd_trigger(provider: Any, args: argparse.Namespace) -> None:
    vars_parsed = parse_variables(args.variables)
    do_trigger(provider, args.ref, vars_parsed, args.dry_run)


def _cmd_cancel(provider: Any, args: argparse.Namespace) -> None:
    do_cancel(provider, args.pipeline_id, args.dry_run)


def _cmd_retry(provider: Any, args: argparse.Namespace) -> None:
    do_retry(provider, args.pipeline_id, args.dry_run)


def _cmd_list(provider: Any, args: argparse.Namespace) -> None:
    do_list(provider, args.ref, args.status, args.limit)


def _cmd_jobs(provider: Any, args: argparse.Namespace) -> None:
    do_jobs(provider, args.pipeline_id)


def _cmd_trace(provider: Any, args: argparse.Namespace) -> None:
    do_trace(provider, args.job_id)


_COMMANDS: dict[str, Callable[[Any, argparse.Namespace], None]] = {
    "trigger": _cmd_trigger,
    "cancel": _cmd_cancel,
    "retry": _cmd_retry,
    "list": _cmd_list,
    "jobs": _cmd_jobs,
    "trace": _cmd_trace,
}


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    validate_provider_args(args)
    ensure_gitlab_provider(args.provider)
    provider = get_provider(
        args.provider,
        project=args.project,
        token=getattr(args, "token", None),
        verbose=args.verbose,
    )

    handler = _COMMANDS.get(args.command)
    if handler is None:
        parser.error(f"Unknown command: {args.command}")
    handler(provider, args)


if __name__ == "__main__":
    main()
