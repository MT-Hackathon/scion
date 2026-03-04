#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "python-dotenv>=1.0",
#   "httpx>=0.27",
# ]
# ///
"""
Consolidated issue management CLI for GitLab, GitHub, and State GitLab.

Subcommands:
  - create  : create a new issue
  - update  : update title/labels/state for an issue
  - close   : close an issue (optional comment)
  - list    : list issues with optional filters
  - get     : fetch a single issue
  - comment : add a comment to an issue
  - triage  : bulk triage (apply labels and optionally mirror issues)

Shared args:
  --provider gitlab|github|state (default: gitlab)
  --project <path-or-id> (falls back to env per provider)
  --dry-run (preview mutations)
  -v/--verbose
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Literal, Sequence

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

ProviderName = Literal["gitlab", "github", "state"]


# ---------------------------------------------------------------------------
# Helper data structures
# ---------------------------------------------------------------------------

@dataclass
class IssueRef:
    provider: ProviderName
    project: str
    iid: int | None
    number: int | None
    web_url: str | None
    title: str | None
    state: str | None
    labels: list[str]
    body: str | None
    author: str | None


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def request_or_die(provider: Any, method: str, endpoint: str, **kwargs: Any) -> dict[str, Any]:
    """Perform a provider request and exit on failure."""
    result = provider.request(method, endpoint, **kwargs)
    if not result["ok"]:
        detail = result["error"] or f"HTTP {result['status_code']}"
        emit_error(f"{method.upper()} {endpoint} failed: {detail}")
    data = result.get("data")
    if data is None:
        emit_error(f"{method.upper()} {endpoint} returned empty response.")
    if not isinstance(data, dict):
        emit_error(f"{method.upper()} {endpoint} returned unexpected payload.")
    return data


def request_list_or_die(
    provider: Any, method: str, endpoint: str, *, params: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    """Perform a provider request expecting a list payload."""
    result = provider.request(method, endpoint, params=params or {})
    if not result["ok"]:
        detail = result["error"] or f"HTTP {result['status_code']}"
        emit_error(f"{method.upper()} {endpoint} failed: {detail}")
    data = result.get("data")
    if data is None:
        emit_error(f"{method.upper()} {endpoint} returned empty response.")
    if not isinstance(data, list):
        emit_error(f"{method.upper()} {endpoint} returned unexpected payload.")
    return data


# ---------------------------------------------------------------------------
# Provider-specific helpers
# ---------------------------------------------------------------------------


def normalize_state(provider: ProviderName, state: str) -> str:
    """Map friendly state to provider-specific values."""
    if provider in ("gitlab", "state"):
        if state == "open":
            return "opened"
        if state == "closed":
            return "closed"
        return "all"
    return state  # github uses open/closed/all


def issue_url(provider: ProviderName, project: str, iid: int | None, web_url: str | None) -> str | None:
    if web_url:
        return web_url
    if iid is None:
        return None
    if provider == "github":
        return f"https://github.com/{project}/issues/{iid}"
    base = "https://gitlab.com" if provider == "gitlab" else "https://git.mt.gov"
    return f"{base}/{project}/-/issues/{iid}"


def parse_labels_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [label.strip() for label in value.split(",") if label.strip()]


def parse_label_ops(spec: str) -> tuple[list[str], list[str]]:
    """
    Parse label operations string of form "add:x,add:y,remove:z" or "add:x,remove:z".
    Returns (add_list, remove_list).
    """
    add: list[str] = []
    remove: list[str] = []
    if not spec:
        return add, remove
    entries = [part.strip() for part in spec.split(",") if part.strip()]
    for entry in entries:
        if ":" not in entry:
            emit_error(f"Invalid label operation '{entry}'. Use add:<label> or remove:<label>.")
        action, name = entry.split(":", 1)
        name = name.strip()
        if not name:
            emit_error(f"Empty label name in '{entry}'.")
        if action == "add":
            add.append(name)
        elif action == "remove":
            remove.append(name)
        else:
            emit_error(f"Unknown label operation '{action}' in '{entry}'.")
    return add, remove


def resolve_gitlab_assignee(provider: Any, username_or_id: str) -> int:
    """Resolve GitLab assignee (gitlab/state)."""
    raw = username_or_id.strip()
    if not raw:
        emit_error("--assignee must be non-empty.")
    if raw.isdigit():
        value = int(raw)
        if value <= 0:
            emit_error("--assignee numeric ID must be positive.")
        return value

    users = request_list_or_die(provider, "GET", "users", params={"username": raw})
    matches = [u for u in users if isinstance(u.get("id"), int)]
    if len(matches) == 1:
        return int(matches[0]["id"])
    emit_error(f"Unable to resolve assignee '{raw}' to a unique user ID.")
    raise AssertionError("unreachable")


def fetch_issue(provider: Any, provider_name: ProviderName, project: str, iid: int) -> IssueRef:
    """Fetch single issue and normalize into IssueRef."""
    if provider_name == "github":
        data = request_or_die(provider, "GET", f"/repos/{project}/issues/{iid}")
        return IssueRef(
            provider=provider_name,
            project=project,
            iid=None,
            number=data.get("number"),
            web_url=data.get("html_url"),
            title=data.get("title"),
            state=data.get("state"),
            labels=[lbl.get("name", "") for lbl in data.get("labels", []) if isinstance(lbl, dict)],
            body=data.get("body"),
            author=(data.get("user") or {}).get("login"),
        )

    data = request_or_die(provider, "GET", f"/projects/{{project}}/issues/{iid}")
    return IssueRef(
        provider=provider_name,
        project=project,
        iid=data.get("iid"),
        number=None,
        web_url=data.get("web_url"),
        title=data.get("title"),
        state=data.get("state"),
        labels=[lbl for lbl in data.get("labels", []) if isinstance(lbl, str)],
        body=data.get("description"),
        author=(data.get("author") or {}).get("username"),
    )


def fetch_issue_list(
    provider: Any,
    provider_name: ProviderName,
    project: str,
    *,
    state: str,
    labels: list[str],
    limit: int,
    assignee: str | None = None,
) -> list[IssueRef]:
    """Fetch issue list with filters."""
    params: dict[str, Any] = {}
    norm_state = normalize_state(provider_name, state)
    params["state"] = norm_state
    if labels:
        params["labels"] = ",".join(labels)
    if provider_name == "github":
        params["per_page"] = min(limit, 100)
        if assignee:
            params["assignee"] = assignee
        data = request_list_or_die(provider, "GET", f"/repos/{project}/issues", params=params)
        issues = []
        for item in data[:limit]:
            # Skip pull requests returned in the issues API
            if "pull_request" in item:
                continue
            issues.append(
                IssueRef(
                    provider=provider_name,
                    project=project,
                    iid=None,
                    number=item.get("number"),
                    web_url=item.get("html_url"),
                    title=item.get("title"),
                    state=item.get("state"),
                    labels=[lbl.get("name", "") for lbl in item.get("labels", []) if isinstance(lbl, dict)],
                    body=item.get("body"),
                    author=(item.get("user") or {}).get("login"),
                )
            )
        return issues

    params["per_page"] = min(limit, 100)
    if assignee:
        params["assignee_username"] = assignee
    data = request_list_or_die(provider, "GET", "/projects/{project}/issues", params=params)
    return [
        IssueRef(
            provider=provider_name,
            project=project,
            iid=item.get("iid"),
            number=None,
            web_url=item.get("web_url"),
            title=item.get("title"),
            state=item.get("state"),
            labels=[lbl for lbl in item.get("labels", []) if isinstance(lbl, str)],
            body=item.get("description"),
            author=(item.get("author") or {}).get("username"),
        )
        for item in data[:limit]
    ]


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------


def resolve_body(args: argparse.Namespace) -> str | None:
    """Return body text from --body or --body-file; error on conflict."""
    body_file = getattr(args, "body_file", None)
    if args.body and body_file:
        emit_error("--body and --body-file are mutually exclusive.")
    if body_file:
        try:
            return Path(body_file).read_text(encoding="utf-8")
        except OSError as exc:
            emit_error(f"Cannot read --body-file {body_file}: {exc}")
    return args.body


def op_create(provider: Any, provider_name: ProviderName, project: str, args: argparse.Namespace) -> None:
    payload: dict[str, Any] = {"title": args.title}
    body = resolve_body(args)
    if body:
        payload["description" if provider_name != "github" else "body"] = body
    labels = parse_labels_csv(args.labels)
    if labels:
        payload["labels"] = ",".join(labels) if provider_name != "github" else labels
    if args.assignee:
        if provider_name == "github":
            payload["assignees"] = [args.assignee]
        else:
            payload["assignee_ids"] = [resolve_gitlab_assignee(provider, args.assignee)]

    if args.dry_run:
        emit_text(["[dry-run] create issue with payload:", str(payload)])
        return

    endpoint = f"/repos/{project}/issues" if provider_name == "github" else "/projects/{project}/issues"
    data = request_or_die(provider, "POST", endpoint, json=payload)
    url = issue_url(provider_name, project, data.get("iid") or data.get("number"), data.get("web_url") or data.get("html_url"))
    emit_text([f"Created issue: {url}"])


def op_comment(provider: Any, provider_name: ProviderName, project: str, iid: int, body: str | None, dry_run: bool) -> str | None:
    if not body:
        emit_error("--body or --body-file is required for comment.")
    if dry_run:
        emit_text([f"[dry-run] add comment to issue {iid}: {truncate(body, 200)}"])
        return None

    if provider_name == "github":
        data = request_or_die(provider, "POST", f"/repos/{project}/issues/{iid}/comments", json={"body": body})
        return data.get("html_url")
    data = request_or_die(
        provider,
        "POST",
        f"/projects/{{project}}/issues/{iid}/notes",
        json={"body": body},
    )
    return data.get("web_url")


def op_update(provider: Any, provider_name: ProviderName, project: str, args: argparse.Namespace) -> None:
    add_labels, remove_labels = parse_label_ops(args.labels or "")
    payload: dict[str, Any] = {}

    if args.title:
        payload["title"] = args.title
    if provider_name == "github":
        if add_labels or remove_labels:
            current = fetch_issue(provider, provider_name, project, args.iid)
            current_labels = set(current.labels)
            current_labels.update(add_labels)
            current_labels.difference_update(remove_labels)
            payload["labels"] = sorted(current_labels)
        if args.state:
            payload["state"] = "closed" if args.state == "close" else "open"
        if args.dry_run:
            emit_text([f"[dry-run] update issue #{args.iid} with payload:", str(payload)])
            return
        data = request_or_die(provider, "PATCH", f"/repos/{project}/issues/{args.iid}", json=payload)
        emit_text([f"Updated issue: {data.get('html_url')}"])
        return

    # gitlab/state
    if add_labels:
        payload["add_labels"] = ",".join(add_labels)
    if remove_labels:
        payload["remove_labels"] = ",".join(remove_labels)
    if args.state:
        payload["state_event"] = "close" if args.state == "close" else "reopen"

    if args.dry_run:
        emit_text([f"[dry-run] update issue #{args.iid} with payload:", str(payload)])
        return

    data = request_or_die(provider, "PUT", f"/projects/{{project}}/issues/{args.iid}", json=payload)
    emit_text([f"Updated issue: {data.get('web_url')}"])


def op_close(provider: Any, provider_name: ProviderName, project: str, args: argparse.Namespace) -> None:
    comment_url = None
    if args.comment:
        comment_url = op_comment(provider, provider_name, project, args.iid, args.comment, args.dry_run)

    if args.dry_run:
        emit_text([f"[dry-run] close issue #{args.iid}"])
        return

    if provider_name == "github":
        data = request_or_die(
            provider,
            "PATCH",
            f"/repos/{project}/issues/{args.iid}",
            json={"state": "closed"},
        )
        url = data.get("html_url")
    else:
        data = request_or_die(
            provider,
            "PUT",
            f"/projects/{{project}}/issues/{args.iid}",
            json={"state_event": "close"},
        )
        url = data.get("web_url")

    lines = [f"Closed issue: {url}"]
    if comment_url:
        lines.append(f"Comment: {comment_url}")
    emit_text(lines)


def op_get(provider: Any, provider_name: ProviderName, project: str, iid: int) -> None:
    issue = fetch_issue(provider, provider_name, project, iid)
    url = issue_url(provider_name, project, issue.iid or issue.number, issue.web_url)
    label_str = ", ".join(issue.labels) if issue.labels else "none"
    body = issue.body or ""
    emit_markdown(
        "\n".join(
            [
                f"**{issue.title or 'Untitled'}**",
                f"- id: {issue.iid or issue.number}",
                f"- state: {issue.state}",
                f"- labels: {label_str}",
                f"- author: {issue.author}",
                f"- url: {url}",
                "",
                body,
            ]
        )
    )


def op_list(provider: Any, provider_name: ProviderName, project: str, args: argparse.Namespace) -> None:
    labels = parse_labels_csv(args.labels)
    issues = fetch_issue_list(
        provider,
        provider_name,
        project,
        state=args.state,
        labels=labels,
        limit=args.limit,
        assignee=args.assignee,
    )
    lines: list[str] = []
    for issue in issues:
        url = issue_url(provider_name, project, issue.iid or issue.number, issue.web_url) or ""
        label_str = ",".join(issue.labels)
        title = truncate(issue.title or "", 120)
        lines.append(f"{issue.iid or issue.number}: [{issue.state}] {title} ({label_str}) {url}")
    emit_text(lines or ["No issues found."])


# ---------------------------------------------------------------------------
# Triage (bulk) operations
# ---------------------------------------------------------------------------


def parse_issue_list(value: str | None) -> list[int]:
    if not value:
        return []
    entries = [part.strip() for part in value.split(",") if part.strip()]
    if not entries:
        return []
    result: list[int] = []
    for entry in entries:
        if not entry.isdigit():
            emit_error(f"Invalid issue id '{entry}'. Use numeric IDs.")
        num = int(entry)
        if num <= 0:
            emit_error("Issue IDs must be positive.")
        result.append(num)
    return result


def list_project_labels(provider: Any, provider_name: ProviderName, project: str) -> set[str]:
    if provider_name == "github":
        data = request_list_or_die(provider, "GET", f"/repos/{project}/labels")
        return {name for item in data if isinstance((name := item.get("name")), str)}
    data = request_list_or_die(provider, "GET", f"/projects/{{project}}/labels")
    return {name for item in data if isinstance((name := item.get("name")), str)}


def mirror_issue(
    provider: Any,
    provider_name: ProviderName,
    source_issue: IssueRef,
    target_project: str,
    prefix: str,
    allowed_labels: set[str],
    dry_run: bool,
) -> tuple[str | None, str | None]:
    """Mirror a single issue to target project. Returns (mirror_url, comment_url)."""
    mirror_title = f"{prefix} {source_issue.title}".strip() if prefix else (source_issue.title or "Untitled")
    filtered_labels = [lbl for lbl in source_issue.labels if lbl in allowed_labels]
    label_payload: Any = ",".join(filtered_labels) if provider_name != "github" else filtered_labels
    source_url = issue_url(source_issue.provider, source_issue.project, source_issue.iid or source_issue.number, source_issue.web_url)
    description_parts = [source_issue.body or "", "", "---", f"Cross-ref: {source_url}"]
    description = "\n".join(description_parts)

    if dry_run:
        emit_text(
            [
                f"[dry-run] mirror '{source_issue.title}' -> {target_project}",
                f"  title: {mirror_title}",
                f"  labels: {label_payload}",
            ]
        )
        return None, None

    if provider_name == "github":
        payload: dict[str, Any] = {"title": mirror_title, "body": description}
        if filtered_labels:
            payload["labels"] = filtered_labels
        data = request_or_die(provider, "POST", f"/repos/{target_project}/issues", json=payload)
        mirror_url = data.get("html_url")
    else:
        payload = {"title": mirror_title, "description": description}
        if filtered_labels:
            payload["labels"] = label_payload
        data = request_or_die(provider, "POST", f"/projects/{target_project}/issues", json=payload)
        mirror_url = data.get("web_url")

    # comment back on source
    comment_body = f"Mirrored to {mirror_url}"
    comment_url = op_comment(
        provider,
        provider_name,
        source_issue.project,
        (source_issue.iid or source_issue.number or 0),
        comment_body,
        dry_run,
    )
    return mirror_url, comment_url


def apply_labels_to_issue(
    provider: Any,
    provider_name: ProviderName,
    project: str,
    iid: int,
    labels: list[str],
    dry_run: bool,
) -> str | None:
    if not labels:
        return None
    if dry_run:
        emit_text([f"[dry-run] add labels to {iid}: {','.join(labels)}"])
        return None
    if provider_name == "github":
        # Merge labels onto existing set
        current = fetch_issue(provider, provider_name, project, iid)
        merged = sorted(set(current.labels).union(labels))
        data = request_or_die(
            provider,
            "PATCH",
            f"/repos/{project}/issues/{iid}",
            json={"labels": merged},
        )
        return data.get("html_url")
    data = request_or_die(
        provider,
        "PUT",
        f"/projects/{{project}}/issues/{iid}",
        json={"add_labels": ",".join(labels)},
    )
    return data.get("web_url")


def op_triage(provider: Any, provider_name: ProviderName, args: argparse.Namespace) -> None:
    source_project = args.source
    if not source_project:
        emit_error("--source is required for triage.")
    _target_project: str | None = args.project or getattr(provider, "project", None)
    if args.mirror and not _target_project:
        emit_error("--project (target) is required when using --mirror. Set via --project or environment.")
    target_project: str = _target_project or ""

    # Separate providers for source/target when paths differ so {project} expansion works.
    source_provider = (
        provider
        if provider.project == source_project
        else get_provider(
            provider_name,
            project=source_project,
            token=getattr(args, "token", None),
            verbose=args.verbose,
        )
    )
    target_provider = (
        provider
        if provider.project == target_project
        else get_provider(
            provider_name,
            project=target_project,
            token=getattr(args, "token", None),
            verbose=args.verbose,
        )
    )

    issue_ids = parse_issue_list(args.issues)
    if not issue_ids:
        fetched = fetch_issue_list(
            source_provider,
            provider_name,
            source_project,
            state="open",
            labels=parse_labels_csv(args.labels),
            limit=args.limit,
        )
        issue_ids = [item.iid or item.number or 0 for item in fetched if (item.iid or item.number)]

    if not issue_ids:
        emit_text(["No issues to triage."])
        return

    allowed_target_labels: set[str] = set()
    if args.mirror:
        allowed_target_labels = list_project_labels(target_provider, provider_name, target_project)

    results: list[str] = []
    for iid in issue_ids:
        issue = fetch_issue(source_provider, provider_name, source_project, iid)
        if args.labels:
            lbls = parse_labels_csv(args.labels)
            apply_labels_to_issue(source_provider, provider_name, source_project, iid, lbls, args.dry_run)
        mirror_url = None
        if args.mirror:
            mirror_url, _ = mirror_issue(
                target_provider,
                provider_name,
                issue,
                target_project,
                args.prefix,
                allowed_target_labels,
                args.dry_run,
            )
        url = issue_url(provider_name, source_project, iid, issue.web_url) or f"{iid}"
        if mirror_url:
            results.append(f"{url} -> {mirror_url}")
        else:
            results.append(f"{url} triaged")

    emit_text(results)


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Unified issue management for GitLab, GitHub, and State.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Shared helpers added to each subparser for clarity
    def with_shared(p: argparse.ArgumentParser) -> argparse.ArgumentParser:
        add_provider_args(p)
        add_common_args(p)
        return p

    # create
    p_create = with_shared(subparsers.add_parser("create", help="Create a new issue."))
    p_create.add_argument("--title", required=True, help="Issue title.")
    p_create.add_argument("--body", help="Issue body/description (inline).")
    p_create.add_argument("--body-file", dest="body_file", metavar="PATH", help="Read body from file — avoids shell escaping on Windows.")
    p_create.add_argument("--labels", help="Comma-separated labels.")
    p_create.add_argument("--assignee", help="Assignee username or ID.")

    # update
    p_update = with_shared(subparsers.add_parser("update", help="Update issue fields."))
    p_update.add_argument("iid", type=int, help="Issue IID/number.")
    p_update.add_argument("--title", help="New title.")
    p_update.add_argument("--labels", help="Label operations: add:bug,remove:wip")
    p_update.add_argument("--state", choices=["close", "reopen"], help="Change state.")

    # close
    p_close = with_shared(subparsers.add_parser("close", help="Close an issue."))
    p_close.add_argument("iid", type=int, help="Issue IID/number.")
    p_close.add_argument("--comment", help="Optional closing comment.")

    # list
    p_list = with_shared(subparsers.add_parser("list", help="List issues."))
    p_list.add_argument("--state", choices=["open", "closed", "all"], default="open")
    p_list.add_argument("--labels", help="Comma-separated labels filter.")
    p_list.add_argument("--limit", type=int, default=20, help="Max issues to return.")
    p_list.add_argument("--assignee", help="Assignee username filter.")

    # get
    p_get = with_shared(subparsers.add_parser("get", help="Get single issue."))
    p_get.add_argument("iid", type=int, help="Issue IID/number.")

    # comment
    p_comment = with_shared(subparsers.add_parser("comment", help="Add a comment."))
    p_comment.add_argument("iid", type=int, help="Issue IID/number.")
    p_comment.add_argument("--body", help="Comment text (inline).")
    p_comment.add_argument("--body-file", dest="body_file", metavar="PATH", help="Read comment body from file.")

    # triage
    p_triage = with_shared(subparsers.add_parser("triage", help="Bulk triage / mirror issues."))
    p_triage.add_argument("--source", required=True, help="Source project path or ID.")
    p_triage.add_argument(
        "--issues",
        help="Comma-separated issue IDs to process. If omitted, fetch open issues from source.",
    )
    p_triage.add_argument("--labels", help="Labels to apply to source issues.")
    p_triage.add_argument("--mirror", action="store_true", help="Mirror issues to target project.")
    p_triage.add_argument("--prefix", default="", help="Prefix for mirrored issue titles.")
    p_triage.add_argument("--limit", type=int, default=50, help="Max issues when auto-fetching.")

    return parser


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _cmd_create(
    provider: Any, provider_name: ProviderName, project: str, args: argparse.Namespace
) -> None:
    op_create(provider, provider_name, project, args)


def _cmd_update(
    provider: Any, provider_name: ProviderName, project: str, args: argparse.Namespace
) -> None:
    op_update(provider, provider_name, project, args)


def _cmd_close(
    provider: Any, provider_name: ProviderName, project: str, args: argparse.Namespace
) -> None:
    op_close(provider, provider_name, project, args)


def _cmd_list(
    provider: Any, provider_name: ProviderName, project: str, args: argparse.Namespace
) -> None:
    op_list(provider, provider_name, project, args)


def _cmd_get(
    provider: Any, provider_name: ProviderName, project: str, args: argparse.Namespace
) -> None:
    op_get(provider, provider_name, project, args.iid)


def _cmd_comment(
    provider: Any, provider_name: ProviderName, project: str, args: argparse.Namespace
) -> None:
    op_comment(provider, provider_name, project, args.iid, resolve_body(args), args.dry_run)


def _cmd_triage(
    provider: Any, provider_name: ProviderName, project: str, args: argparse.Namespace
) -> None:
    del project
    op_triage(provider, provider_name, args)


_COMMANDS: dict[str, Callable[[Any, ProviderName, str, argparse.Namespace], None]] = {
    "create": _cmd_create,
    "update": _cmd_update,
    "close": _cmd_close,
    "list": _cmd_list,
    "get": _cmd_get,
    "comment": _cmd_comment,
    "triage": _cmd_triage,
}


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    validate_provider_args(args)
    provider_name: ProviderName = args.provider
    provider = get_provider(
        provider_name,
        project=args.project,
        token=getattr(args, "token", None),
        verbose=args.verbose,
    )
    project = getattr(provider, "project", None)
    if not project:
        emit_error("Project must be provided via --project or environment.")

    handler = _COMMANDS.get(args.command)
    if handler is None:
        parser.error(f"Unknown command: {args.command}")
    handler(provider, provider_name, project, args)


if __name__ == "__main__":
    main()
