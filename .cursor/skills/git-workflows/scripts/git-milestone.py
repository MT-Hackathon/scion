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
import datetime as dt
from collections.abc import Callable
from typing import Any, Sequence

from _core import (
    add_common_args,
    add_provider_args,
    emit_error,
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


def to_github_due(date_str: str | None) -> str | None:
    if not date_str:
        return None
    try:
        parsed = dt.date.fromisoformat(date_str)
        return f"{parsed.isoformat()}T00:00:00Z"
    except ValueError:
        emit_error("Invalid --due date. Use YYYY-MM-DD.")
    return None


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------


def op_create(provider: Any, provider_name: str, args: argparse.Namespace) -> None:
    project = ensure_project(provider)
    if args.dry_run:
        emit_text(
            [
                "[dry-run] create milestone",
                f"title={args.title}",
                f"due={args.due or '(none)'}",
            ]
        )
        return

    if provider_name in ("gitlab", "state"):
        payload: dict[str, Any] = {"title": args.title}
        if args.due:
            payload["due_date"] = args.due
        if args.description:
            payload["description"] = args.description
        result = provider.request("POST", "/projects/{project}/milestones", json=payload)
        data = ensure_ok_dict(result, "Create milestone")
        emit_text([f"Created milestone {data.get('id')} {data.get('title')}"])
    else:
        payload = {"title": args.title}
        gh_due = to_github_due(args.due)
        if gh_due:
            payload["due_on"] = gh_due
        if args.description:
            payload["description"] = args.description
        result = provider.request("POST", f"/repos/{project}/milestones", json=payload)
        data = ensure_ok_dict(result, "Create milestone")
        emit_text([f"Created milestone {data.get('number')} {data.get('title')}"])


def op_list(provider: Any, provider_name: str, args: argparse.Namespace) -> None:
    project = ensure_project(provider)
    if provider_name in ("gitlab", "state"):
        params = {"state": args.state, "per_page": "100"}
        result = provider.request("GET", "/projects/{project}/milestones", params=params)
    else:
        state = "open" if args.state == "active" else args.state
        result = provider.request(
            "GET",
            f"/repos/{project}/milestones",
            params={"state": state, "per_page": "100"},
        )
    items = ensure_ok_list(result, "List milestones")
    lines = []
    for item in items:
        ident = item.get("id") if provider_name in ("gitlab", "state") else item.get("number")
        state = item.get("state") or ""
        title = item.get("title") or ""
        due = item.get("due_date") or item.get("due_on") or ""
        lines.append(f"- {ident}: [{state}] {title} due={due}")
    emit_text(lines or ["(no milestones)"])


def op_delete(provider: Any, provider_name: str, args: argparse.Namespace) -> None:
    project = ensure_project(provider)
    if args.dry_run:
        emit_text([f"[dry-run] delete milestone {args.milestone_id}"])
        return

    if provider_name in ("gitlab", "state"):
        endpoint = f"/projects/{{project}}/milestones/{args.milestone_id}"
    else:
        endpoint = f"/repos/{project}/milestones/{args.milestone_id}"

    result = provider.request("DELETE", endpoint)
    if not result.get("ok"):
        status = result.get("status_code")
        detail = result.get("error") or "Unknown error"
        emit_error(f"Delete failed (HTTP {status}): {detail}")
    emit_text([f"Deleted milestone {args.milestone_id}"])


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage milestones across providers.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def with_shared(p: argparse.ArgumentParser) -> argparse.ArgumentParser:
        add_provider_args(p)
        add_common_args(p)
        return p

    p_create = with_shared(subparsers.add_parser("create", help="Create a milestone."))
    p_create.add_argument("--title", required=True, help="Milestone title.")
    p_create.add_argument("--due", help="Due date (YYYY-MM-DD).")
    p_create.add_argument("--description", help="Description.")

    p_list = with_shared(subparsers.add_parser("list", help="List milestones."))
    p_list.add_argument(
        "--state",
        choices=["active", "closed", "all"],
        default="active",
        help="Milestone state filter.",
    )

    p_delete = with_shared(subparsers.add_parser("delete", help="Delete a milestone."))
    p_delete.add_argument("milestone_id", type=int, help="Milestone ID/number.")

    return parser


def _cmd_create(provider: Any, provider_name: str, args: argparse.Namespace) -> None:
    op_create(provider, provider_name, args)


def _cmd_list(provider: Any, provider_name: str, args: argparse.Namespace) -> None:
    op_list(provider, provider_name, args)


def _cmd_delete(provider: Any, provider_name: str, args: argparse.Namespace) -> None:
    op_delete(provider, provider_name, args)


_COMMANDS: dict[str, Callable[[Any, str, argparse.Namespace], None]] = {
    "create": _cmd_create,
    "list": _cmd_list,
    "delete": _cmd_delete,
}


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    validate_provider_args(args)
    provider = get_provider(
        args.provider,
        project=args.project,
        token=getattr(args, "token", None),
        verbose=args.verbose,
    )

    handler = _COMMANDS.get(args.command)
    if handler is None:
        parser.error(f"Unknown command: {args.command}")
    handler(provider, args.provider, args)


if __name__ == "__main__":
    main()
