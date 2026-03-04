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
import json
import re
import urllib.parse
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


def ensure_gitlab(provider_name: str) -> None:
    if provider_name == "github":
        emit_error("git-epic supports gitlab/state providers only.")


def ensure_project(provider: Any) -> str:
    project = getattr(provider, "project", None)
    if not project:
        emit_error("Project must be provided via --project or environment.")
    return str(project)


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


def group_path_from_project(project: str) -> str:
    if "/" not in project:
        emit_error("Project path must include group, e.g., group/project.")
    return project.rsplit("/", 1)[0]


def encoded_group_id(group_path: str) -> str:
    """URL-encode group path for GitLab API (handles nested groups)."""
    return urllib.parse.quote(group_path, safe="")


def _extract_section(description: str, header_pattern: str) -> str | None:
    """Extract content under a markdown section header."""
    if not description:
        return None
    pattern = re.compile(
        rf"^##\s*{re.escape(header_pattern)}\s*$",
        re.IGNORECASE | re.MULTILINE,
    )
    match = pattern.search(description)
    if not match:
        return None
    start = match.end()
    next_section = re.search(r"\n##\s+", description[start:])
    end = start + next_section.start() if next_section else len(description)
    return description[start:end].strip() or None


def _extract_given_when_then(description: str) -> str | None:
    """Extract GIVEN/WHEN/THEN blocks from description."""
    if not description:
        return None
    pattern = re.compile(
        r"(GIVEN\s+.+?)(?=GIVEN|WHEN|$)|(WHEN\s+.+?)(?=GIVEN|WHEN|THEN|$)|(THEN\s+.+?)(?=GIVEN|WHEN|THEN|$)",
        re.IGNORECASE | re.DOTALL,
    )
    blocks: list[str] = []
    for m in pattern.finditer(description):
        block = (m.group(1) or m.group(2) or m.group(3) or "").strip()
        if block:
            blocks.append(block)
    return "\n".join(blocks) if blocks else None


def _extract_acceptance_criteria(description: str) -> str:
    """Extract acceptance criteria from issue description."""
    ac = _extract_section(description, "Acceptance Criteria")
    if ac:
        return ac
    ac = _extract_section(description, "AC")
    if ac:
        return ac
    gwt = _extract_given_when_then(description)
    if gwt:
        return gwt
    return "No acceptance criteria found"


def _extract_scope(description: str) -> str:
    """Extract scope section from issue description."""
    scope = _extract_section(description, "Scope")
    return scope if scope else ""


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------


def op_create(provider: Any, args: argparse.Namespace) -> None:
    project = ensure_project(provider)
    group_path = group_path_from_project(project)
    payload: dict[str, Any] = {"title": args.title}
    if args.description:
        payload["description"] = args.description
    if args.labels:
        payload["labels"] = args.labels

    if args.dry_run:
        emit_text(
            [
                f"[dry-run] create epic in {group_path}",
                f"title={args.title}",
                f"labels={args.labels or ''}",
            ]
        )
        return

    endpoint = f"/groups/{group_path}/epics"
    result = provider.request("POST", endpoint, json=payload)
    data = ensure_ok_dict(result, "Create epic")
    emit_text([f"Created epic !{data.get('iid')} {data.get('web_url','')}"])


def op_list(provider: Any, args: argparse.Namespace) -> None:
    project = ensure_project(provider)
    group_path = group_path_from_project(project)
    params = {
        "state": args.state,
        "per_page": str(min(args.limit, 100)),
        "sort": "desc",
    }
    endpoint = f"/groups/{group_path}/epics"
    result = provider.request("GET", endpoint, params=params)
    items = ensure_ok_list(result, "List epics")[: args.limit]
    lines = []
    for item in items:
        line = f"!{item.get('iid')}: [{item.get('state')}] {truncate(item.get('title') or '', 140)}"
        if item.get("web_url"):
            line += f" {item['web_url']}"
        lines.append(line)
    emit_text(lines or ["(no epics)"])


def op_get(provider: Any, args: argparse.Namespace) -> dict[str, Any]:
    project = ensure_project(provider)
    group_path = group_path_from_project(project)
    endpoint = f"/groups/{group_path}/epics/{args.epic_id}"
    result = provider.request("GET", endpoint)
    data = ensure_ok_dict(result, "Get epic")
    description = data.get("description") or ""
    emit_markdown(
        "\n".join(
            [
                f"**!{data.get('iid')}: {data.get('title','')}**",
                f"- state: {data.get('state')}",
                f"- labels: {', '.join(data.get('labels', []))}",
                f"- url: {data.get('web_url')}",
                "",
                truncate(description, 2000),
            ]
        )
    )
    return data


def op_link(provider: Any, args: argparse.Namespace) -> None:
    project = ensure_project(provider)
    epic = op_get(provider, args)
    epic_global_id = epic.get("id")
    if not isinstance(epic_global_id, int):
        emit_error("Epic ID missing from response; cannot link issue.")

    if args.dry_run:
        emit_text(
            [
                f"[dry-run] link issue {args.issue_iid} to epic id={epic_global_id}",
                f"project={project}",
            ]
        )
        return

    endpoint = f"/projects/{{project}}/issues/{args.issue_iid}"
    payload = {"epic_id": epic_global_id}
    result = provider.request("PUT", endpoint, json=payload)
    ensure_ok_dict(result, "Link issue to epic")
    emit_text([f"Linked issue {args.issue_iid} to epic !{epic.get('iid')}"])


def _fetch_all_epic_issues(
    provider: Any,
    group_id: str,
    epic_iid: int,
    include_closed: bool,
    project_id: int | None,
) -> list[dict[str, Any]]:
    """Fetch all issues for an epic with pagination."""
    endpoint = f"/groups/{group_id}/epics/{epic_iid}/issues"
    per_page = 100
    page = 1
    all_issues: list[dict[str, Any]] = []
    while True:
        params: dict[str, Any] = {
            "per_page": str(per_page),
            "page": str(page),
        }
        result = provider.request("GET", endpoint, params=params)
        items = ensure_ok_list(result, "List epic issues")
        for item in items:
            if not include_closed and item.get("state") != "opened":
                continue
            if project_id is not None and item.get("project_id") != project_id:
                continue
            all_issues.append(item)
        if len(items) < per_page:
            break
        page += 1
    return all_issues


def _format_assignee(issue: dict[str, Any]) -> str:
    """Format assignee(s) for display."""
    assignees = issue.get("assignees") or []
    if not assignees and issue.get("assignee"):
        assignees = [issue["assignee"]]
    if not assignees:
        return "—"
    names = [a.get("username") or a.get("name") or "?" for a in assignees]
    return ", ".join(names)


def op_pull(provider: Any, args: argparse.Namespace) -> None:
    """Fetch all issues for an epic and produce a structured brief or JSON."""
    project = ensure_project(provider)
    group_path = group_path_from_project(project)
    group_id = encoded_group_id(group_path)
    epic_iid = args.epic_iid

    endpoint = f"/groups/{group_id}/epics/{epic_iid}"
    result = provider.request("GET", endpoint)
    epic = ensure_ok_dict(result, "Get epic")

    issues = _fetch_all_epic_issues(
        provider,
        group_id,
        epic_iid,
        include_closed=getattr(args, "include_closed", False),
        project_id=getattr(args, "project_id", None),
    )

    if args.format == "json":
        payload: dict[str, Any] = {
            "epic": epic,
            "issues": issues,
        }
        emit_text([json.dumps(payload, indent=2)])
        return

    # Brief format
    open_count = sum(1 for i in issues if i.get("state") == "opened")
    closed_count = len(issues) - open_count
    all_labels: set[str] = set()
    missing_ac: list[str] = []

    lines = [
        f"# Epic: {epic.get('title', '')} (IID: {epic_iid})",
        f"State: {epic.get('state', '')} | Created: {epic.get('created_at', '')[:10]}",
        "",
        "## Description",
        epic.get("description") or "(no description)",
        "",
        f"## Issues ({open_count} open, {closed_count} closed)",
        "",
    ]

    for issue in issues:
        title = issue.get("title") or "(no title)"
        iid = issue.get("iid", "?")
        state = issue.get("state", "")
        labels = issue.get("labels") or []
        all_labels.update(labels)
        assignee = _format_assignee(issue)
        milestone_obj = issue.get("milestone")
        milestone = milestone_obj.get("title", "—") if isinstance(milestone_obj, dict) else "—"

        desc = issue.get("description") or ""
        ac = _extract_acceptance_criteria(desc)
        if "No acceptance criteria found" in ac:
            missing_ac.append(title)
        scope = _extract_scope(desc)

        lines.extend(
            [
                f"### {title} (#{iid})",
                f"- **State**: {state} | **Labels**: {', '.join(labels) or '—'} | **Assignee**: {assignee}",
                f"- **Milestone**: {milestone}",
                "",
                "#### Acceptance Criteria",
                ac,
                "",
            ]
        )
        if scope:
            lines.extend(["#### Scope", scope, ""])
        lines.append("---")
        lines.append("")

    lines.extend(
        [
            "## Summary",
            f"- Open: {open_count} | Closed: {closed_count} | Total: {len(issues)}",
            f"- Missing acceptance criteria: {', '.join(missing_ac) if missing_ac else 'none'}",
            f"- Labels in use: {', '.join(sorted(all_labels)) if all_labels else 'none'}",
        ]
    )

    emit_markdown("\n".join(lines))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage GitLab epics.")
    add_provider_args(parser)
    add_common_args(parser)
    subs = parser.add_subparsers(dest="command", required=True)

    p_create = subs.add_parser("create", help="Create a new epic.")
    p_create.add_argument("--title", required=True, help="Epic title.")
    p_create.add_argument("--description", help="Epic description.")
    p_create.add_argument("--labels", help="Comma-separated labels.")

    p_list = subs.add_parser("list", help="List epics.")
    p_list.add_argument(
        "--state",
        choices=["opened", "closed", "all"],
        default="opened",
        help="Epic state filter.",
    )
    p_list.add_argument("--limit", type=int, default=20, help="Max epics to return.")

    p_get = subs.add_parser("get", help="Fetch a single epic.")
    p_get.add_argument("epic_id", type=int, help="Epic IID.")

    p_link = subs.add_parser("link", help="Link an issue to an epic.")
    p_link.add_argument("epic_id", type=int, help="Epic IID.")
    p_link.add_argument("issue_iid", type=int, help="Issue IID to link.")

    p_pull = subs.add_parser(
        "pull",
        help="Fetch all issues for an epic and produce a structured brief for LLM consumption.",
    )
    p_pull.add_argument("epic_iid", type=int, help="Epic IID within the group.")
    p_pull.add_argument(
        "--format",
        choices=["brief", "json"],
        default="brief",
        help="Output format: brief (markdown) or json.",
    )
    p_pull.add_argument(
        "--include-closed",
        action="store_true",
        help="Include closed issues (default: open only).",
    )
    p_pull.add_argument(
        "--project-id",
        type=int,
        metavar="ID",
        help="Filter to issues in a specific project.",
    )

    return parser


def _cmd_create(provider: Any, args: argparse.Namespace) -> None:
    op_create(provider, args)


def _cmd_list(provider: Any, args: argparse.Namespace) -> None:
    op_list(provider, args)


def _cmd_get(provider: Any, args: argparse.Namespace) -> None:
    op_get(provider, args)


def _cmd_link(provider: Any, args: argparse.Namespace) -> None:
    op_link(provider, args)


def _cmd_pull(provider: Any, args: argparse.Namespace) -> None:
    op_pull(provider, args)


_COMMANDS: dict[str, Callable[[Any, argparse.Namespace], None]] = {
    "create": _cmd_create,
    "list": _cmd_list,
    "get": _cmd_get,
    "link": _cmd_link,
    "pull": _cmd_pull,
}


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    validate_provider_args(args)
    ensure_gitlab(args.provider)
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
