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
from typing import Any, Iterable

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


# ---------- Helpers ----------

def ensure_project(provider: Any) -> str:
    project = getattr(provider, "project", None)
    if not project:
        emit_error("Missing project. Provide --project or set provider env.")
    return project


def ensure_ok(result: Any, context: str) -> Any:
    if result.get("ok"):
        return result.get("data")
    status = result.get("status_code")
    detail = result.get("error") or "Unknown error"
    emit_error(f"{context} failed (HTTP {status}): {detail}")


def prefix_for(provider_name: str) -> str:
    return "!" if provider_name in ("gitlab", "state") else "#"


def maybe_truncate(text: str | None, limit: int = 200) -> str:
    if not text:
        return ""
    return truncate(text, limit)


def dry_run_guard(enabled: bool, message: str) -> bool:
    if enabled:
        emit_text([f"[dry-run] {message}"])
        return True
    return False


# ---------- GitLab / State GitLab ----------

def gitlab_create(
    provider: Any,
    source: str,
    target: str,
    title: str,
    body: str | None,
    draft: bool,
    dry_run: bool,
) -> dict[str, Any]:
    if draft and not title.lower().startswith(("draft:", "wip:")):
        title = f"Draft: {title}"
    payload: dict[str, Any] = {
        "source_branch": source,
        "target_branch": target,
        "title": title,
    }
    if body:
        payload["description"] = body

    if dry_run and dry_run_guard(True, f"Would create MR {source}->{target}"):
        return {"web_url": None, "iid": None}

    project = ensure_project(provider)
    result = provider.request(
        "POST",
        "projects/{project}/merge_requests",
        json=payload,
    )
    return ensure_ok(result, "Create MR")


def gitlab_merge(
    provider: Any,
    iid: int,
    squash: bool,
    delete_branch: bool,
    message: str | None,
    dry_run: bool,
) -> dict[str, Any]:
    if dry_run and dry_run_guard(True, f"Would merge MR {iid}"):
        return {"web_url": None}

    payload: dict[str, Any] = {
        "squash": squash,
        "should_remove_source_branch": delete_branch,
    }
    if message:
        payload["merge_commit_message"] = message

    project = ensure_project(provider)
    result = provider.request(
        "PUT",
        f"projects/{{project}}/merge_requests/{iid}/merge",
        json=payload,
    )
    return ensure_ok(result, "Merge MR")


def gitlab_close_reopen(
    provider: Any,
    iid: int,
    state: str,
    dry_run: bool,
) -> dict[str, Any]:
    if dry_run and dry_run_guard(True, f"Would set MR {iid} state={state}"):
        return {"web_url": None}

    project = ensure_project(provider)
    result = provider.request(
        "PUT",
        f"projects/{{project}}/merge_requests/{iid}",
        json={"state_event": state},
    )
    return ensure_ok(result, f"{state.title()} MR")


def gitlab_comment(
    provider: Any,
    iid: int,
    body: str,
    dry_run: bool,
) -> dict[str, Any]:
    if dry_run and dry_run_guard(True, f"Would comment on MR {iid}"):
        return {"web_url": None}

    project = ensure_project(provider)
    result = provider.request(
        "POST",
        f"projects/{{project}}/merge_requests/{iid}/notes",
        json={"body": body},
    )
    return ensure_ok(result, "Comment on MR")


def gitlab_get(provider: Any, iid: int) -> dict[str, Any]:
    project = ensure_project(provider)
    result = provider.request(
        "GET",
        f"projects/{{project}}/merge_requests/{iid}",
    )
    return ensure_ok(result, "Get MR")


def gitlab_list(
    provider: Any,
    state: str,
    author: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    project = ensure_project(provider)
    state_map = {"open": "opened", "merged": "merged", "closed": "closed", "all": "all"}
    params: dict[str, Any] = {
        "state": state_map.get(state, "opened"),
        "per_page": str(min(limit, 100)),
    }
    if author:
        params["author_username"] = author
    result = provider.request(
        "GET",
        "projects/{project}/merge_requests",
        params=params,
    )
    data = ensure_ok(result, "List MRs")
    return list(data)[:limit] if isinstance(data, list) else []


def gitlab_notes(
    provider: Any,
    iid: int,
    limit: int,
) -> list[dict[str, Any]]:
    project = ensure_project(provider)
    result = provider.request(
        "GET",
        f"projects/{{project}}/merge_requests/{iid}/notes",
        params={"per_page": str(min(limit, 100)), "sort": "asc"},
    )
    data = ensure_ok(result, "Fetch MR notes")
    return list(data)[:limit] if isinstance(data, list) else []


def gitlab_discussions(
    provider: Any,
    iid: int,
) -> list[dict[str, Any]]:
    """Fetch all discussions for a merge request."""
    project = ensure_project(provider)
    result = provider.request(
        "GET",
        f"projects/{{project}}/merge_requests/{iid}/discussions",
        params={"per_page": "100"},
    )
    data = ensure_ok(result, "Fetch MR discussions")
    return list(data) if isinstance(data, list) else []


def gitlab_resolve_discussion(
    provider: Any,
    iid: int,
    discussion_id: str,
    dry_run: bool,
) -> dict[str, Any]:
    """Resolve a specific discussion thread."""
    if dry_run and dry_run_guard(True, f"Would resolve discussion {discussion_id}"):
        return {"resolved": True}

    project = ensure_project(provider)
    result = provider.request(
        "PUT",
        f"projects/{{project}}/merge_requests/{iid}/discussions/{discussion_id}",
        json={"resolved": True},
    )
    return ensure_ok(result, f"Resolve discussion {discussion_id}")


# ---------- GitHub ----------

def github_create(
    provider: Any,
    source: str,
    target: str,
    title: str,
    body: str | None,
    draft: bool,
    dry_run: bool,
) -> dict[str, Any]:
    if dry_run and dry_run_guard(True, f"Would create PR {source}->{target}"):
        return {"html_url": None, "number": None}

    payload: dict[str, Any] = {
        "head": source,
        "base": target,
        "title": title,
        "draft": draft,
    }
    if body:
        payload["body"] = body

    project = ensure_project(provider)
    result = provider.request(
        "POST",
        f"repos/{project}/pulls",
        json=payload,
    )
    return ensure_ok(result, "Create PR")


def github_merge(
    provider: Any,
    iid: int,
    squash: bool,
    delete_branch: bool,
    message: str | None,
    dry_run: bool,
) -> dict[str, Any]:
    if dry_run and dry_run_guard(True, f"Would merge PR {iid}"):
        return {"html_url": None}

    payload: dict[str, Any] = {
        "merge_method": "squash" if squash else "merge",
        "delete_head_ref": delete_branch,
    }
    if message:
        payload["commit_message"] = message

    project = ensure_project(provider)
    result = provider.request(
        "PUT",
        f"repos/{project}/pulls/{iid}/merge",
        json=payload,
    )
    return ensure_ok(result, "Merge PR")


def github_close_reopen(
    provider: Any,
    iid: int,
    state: str,
    dry_run: bool,
) -> dict[str, Any]:
    if dry_run and dry_run_guard(True, f"Would set PR {iid} state={state}"):
        return {"html_url": None}

    project = ensure_project(provider)
    result = provider.request(
        "PATCH",
        f"repos/{project}/pulls/{iid}",
        json={"state": state},
    )
    return ensure_ok(result, f"{state.title()} PR")


def github_comment(
    provider: Any,
    iid: int,
    body: str,
    dry_run: bool,
) -> dict[str, Any]:
    if dry_run and dry_run_guard(True, f"Would comment on PR {iid}"):
        return {"html_url": None}

    project = ensure_project(provider)
    result = provider.request(
        "POST",
        f"repos/{project}/issues/{iid}/comments",
        json={"body": body},
    )
    return ensure_ok(result, "Comment on PR")


def github_get(provider: Any, iid: int) -> dict[str, Any]:
    project = ensure_project(provider)
    result = provider.request(
        "GET",
        f"repos/{project}/pulls/{iid}",
    )
    return ensure_ok(result, "Get PR")


def github_list(
    provider: Any,
    state: str,
    author: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    project = ensure_project(provider)
    gh_state = "open"
    if state in ("closed", "all"):
        gh_state = state
    if state == "merged":
        gh_state = "closed"
    params: dict[str, Any] = {"state": gh_state, "per_page": str(min(limit, 100))}
    if author:
        params["creator"] = author

    result = provider.request(
        "GET",
        f"repos/{project}/pulls",
        params=params,
    )
    data = ensure_ok(result, "List PRs")
    items: list[dict[str, Any]] = list(data) if isinstance(data, list) else []

    if state == "merged":
        merged: list[dict[str, Any]] = []
        for pr in items:
            if pr.get("merged_at"):
                merged.append(pr)
            if len(merged) >= limit:
                break
        return merged

    return items[:limit]


def github_notes(
    provider: Any,
    iid: int,
    limit: int,
) -> list[dict[str, Any]]:
    project = ensure_project(provider)
    result = provider.request(
        "GET",
        f"repos/{project}/issues/{iid}/comments",
        params={"per_page": str(min(limit, 100))},
    )
    data = ensure_ok(result, "Fetch PR comments")
    return list(data)[:limit] if isinstance(data, list) else []


# ---------- Formatting ----------

def render_list(
    provider_name: str,
    items: list[dict[str, Any]],
) -> None:
    prefix = prefix_for(provider_name)
    lines: list[str] = []
    for item in items:
        iid = item.get("iid") if prefix == "!" else item.get("number")
        title = item.get("title") or ""
        state = item.get("state") or ""
        source = item.get("source_branch") or item.get("head", {}).get("ref") or ""
        target = item.get("target_branch") or item.get("base", {}).get("ref") or ""
        author = (
            (item.get("author") or {}).get("username")
            if prefix == "!"
            else (item.get("user") or {}).get("login")
        )
        url = item.get("web_url") or item.get("html_url") or ""
        draft = item.get("draft") or False
        label = f"{prefix}{iid}" if iid is not None else prefix
        draft_tag = " [draft]" if draft else ""
        line = f"- {label} {state}{draft_tag}: {source}->{target} {maybe_truncate(title, 120)}"
        if author:
            line += f" (by {author})"
        if url:
            line += f" {url}"
        lines.append(line)
    emit_text(lines or ["(no results)"])


def render_single(provider_name: str, item: dict[str, Any]) -> None:
    prefix = prefix_for(provider_name)
    iid = item.get("iid") if prefix == "!" else item.get("number")
    title = item.get("title") or ""
    state = item.get("state") or ""
    url = item.get("web_url") or item.get("html_url") or ""
    author = (
        (item.get("author") or {}).get("username")
        if prefix == "!"
        else (item.get("user") or {}).get("login")
    )
    description = item.get("description") or item.get("body") or ""
    source = item.get("source_branch") or item.get("head", {}).get("ref") or ""
    target = item.get("target_branch") or item.get("base", {}).get("ref") or ""
    draft = item.get("draft") or False
    lines = [
        f"{prefix}{iid} {state}{' [draft]' if draft else ''}: {maybe_truncate(title, 200)}",
        f"source: {source} -> target: {target}",
    ]
    if author:
        lines.append(f"author: {author}")
    if url:
        lines.append(f"url: {url}")
    if description:
        lines.append("")
        lines.append(maybe_truncate(description, 800))
    emit_text(lines)


def render_notes(
    provider_name: str,
    iid: int,
    notes: list[dict[str, Any]],
    *,
    author_filter: str | None = None,
    full: bool = False,
) -> None:
    prefix = prefix_for(provider_name)
    filtered: list[str] = []
    for note in notes:
        author = (
            (note.get("author") or {}).get("username")
            if prefix == "!"
            else (note.get("user") or {}).get("login")
        )
        if author_filter and author_filter.lower() not in (author or "").lower():
            continue
        body = note.get("body") or note.get("comment") or note.get("body_text") or ""
        note_id = note.get("id") or note.get("node_id") or ""
        display_body = body if full else maybe_truncate(body, 500)
        filtered.append(f"- [{note_id}] {author or 'unknown'}: {display_body}")
    header = f"Notes for {prefix}{iid} ({len(filtered)} shown"
    if author_filter:
        header += f", filtered by '{author_filter}'"
    header += "):"
    emit_text([header] + filtered if filtered else [header, "(no matching notes)"])


# ---------- Command Handlers ----------

def handle_create(args: argparse.Namespace) -> None:
    provider = get_provider(
        args.provider,
        project=args.project,
        token=args.token,
        verbose=args.verbose,
    )
    if args.provider in ("gitlab", "state"):
        data = gitlab_create(
            provider,
            args.source,
            args.target,
            args.title,
            args.body,
            args.draft,
            args.dry_run,
        )
        iid = data.get("iid")
        url = data.get("web_url") or ""
        emit_text([f"Created MR !{iid} {url}" if iid else "MR create completed."])
    else:
        data = github_create(
            provider,
            args.source,
            args.target,
            args.title,
            args.body,
            args.draft,
            args.dry_run,
        )
        num = data.get("number")
        url = data.get("html_url") or ""
        emit_text([f"Created PR #{num} {url}" if num else "PR create completed."])


def handle_merge(args: argparse.Namespace) -> None:
    provider = get_provider(
        args.provider,
        project=args.project,
        token=args.token,
        verbose=args.verbose,
    )
    if args.provider in ("gitlab", "state"):
        data = gitlab_merge(
            provider,
            args.iid,
            args.squash,
            args.delete_branch,
            args.message,
            args.dry_run,
        )
        url = data.get("web_url") or ""
        emit_text([f"Merged MR !{args.iid} {'(squash)' if args.squash else ''} {url}".strip()])
    else:
        data = github_merge(
            provider,
            args.iid,
            args.squash,
            args.delete_branch,
            args.message,
            args.dry_run,
        )
        url = data.get("html_url") or ""
        emit_text([f"Merged PR #{args.iid} {'(squash)' if args.squash else ''} {url}".strip()])


def handle_close(args: argparse.Namespace) -> None:
    provider = get_provider(
        args.provider,
        project=args.project,
        token=args.token,
        verbose=args.verbose,
    )
    if args.provider in ("gitlab", "state"):
        data = gitlab_close_reopen(provider, args.iid, "close", args.dry_run)
        url = data.get("web_url") or ""
        emit_text([f"Closed MR !{args.iid} {url}".strip()])
        if args.comment:
            gitlab_comment(provider, args.iid, args.comment, args.dry_run)
    else:
        data = github_close_reopen(provider, args.iid, "closed", args.dry_run)
        url = data.get("html_url") or ""
        emit_text([f"Closed PR #{args.iid} {url}".strip()])
        if args.comment:
            github_comment(provider, args.iid, args.comment, args.dry_run)


def handle_reopen(args: argparse.Namespace) -> None:
    provider = get_provider(
        args.provider,
        project=args.project,
        token=args.token,
        verbose=args.verbose,
    )
    if args.provider in ("gitlab", "state"):
        data = gitlab_close_reopen(provider, args.iid, "reopen", args.dry_run)
        url = data.get("web_url") or ""
        emit_text([f"Reopened MR !{args.iid} {url}".strip()])
    else:
        data = github_close_reopen(provider, args.iid, "open", args.dry_run)
        url = data.get("html_url") or ""
        emit_text([f"Reopened PR #{args.iid} {url}".strip()])


def handle_comment(args: argparse.Namespace) -> None:
    provider = get_provider(
        args.provider,
        project=args.project,
        token=args.token,
        verbose=args.verbose,
    )
    if args.provider in ("gitlab", "state"):
        gitlab_comment(provider, args.iid, args.body, args.dry_run)
        emit_text([f"Commented on MR !{args.iid}"])
    else:
        github_comment(provider, args.iid, args.body, args.dry_run)
        emit_text([f"Commented on PR #{args.iid}"])


def handle_list(args: argparse.Namespace) -> None:
    provider = get_provider(
        args.provider,
        project=args.project,
        token=args.token,
        verbose=args.verbose,
    )
    if args.provider in ("gitlab", "state"):
        items = gitlab_list(provider, args.state, args.author, args.limit)
    else:
        items = github_list(provider, args.state, args.author, args.limit)
    render_list(args.provider, items)


def handle_get(args: argparse.Namespace) -> None:
    provider = get_provider(
        args.provider,
        project=args.project,
        token=args.token,
        verbose=args.verbose,
    )
    if args.provider in ("gitlab", "state"):
        item = gitlab_get(provider, args.iid)
    else:
        item = github_get(provider, args.iid)
    render_single(args.provider, item)


def handle_notes(args: argparse.Namespace) -> None:
    provider = get_provider(
        args.provider,
        project=args.project,
        token=args.token,
        verbose=args.verbose,
    )
    if args.provider in ("gitlab", "state"):
        notes = gitlab_notes(provider, args.iid, args.limit)
    else:
        notes = github_notes(provider, args.iid, args.limit)
    render_notes(
        args.provider,
        args.iid,
        notes,
        author_filter=args.author,
        full=args.full,
    )


def handle_resolve_threads(args: argparse.Namespace) -> None:
    """Resolve discussion threads matching a filter (e.g., bugbot threads)."""
    provider = get_provider(
        args.provider,
        project=args.project,
        token=args.token,
        verbose=args.verbose,
    )
    if args.provider not in ("gitlab", "state"):
        emit_error("resolve-threads is only supported for GitLab/State providers")
        return

    discussions = gitlab_discussions(provider, args.iid)
    resolved_count = 0
    skipped_count = 0

    for discussion in discussions:
        notes = discussion.get("notes", [])
        if not notes:
            continue

        first_note = notes[0]
        author = (first_note.get("author") or {}).get("username", "")
        is_resolvable = first_note.get("resolvable", False)
        is_resolved = first_note.get("resolved", False)

        # Check if this is a bot discussion (bugbot)
        is_bot = "bot" in author.lower()
        if args.author and args.author.lower() not in author.lower():
            continue

        # Only resolve unresolved, resolvable discussions from bots
        if is_bot and is_resolvable and not is_resolved:
            discussion_id = discussion.get("id")
            if discussion_id:
                gitlab_resolve_discussion(provider, args.iid, discussion_id, args.dry_run)
                body_preview = maybe_truncate(first_note.get("body", ""), 80)
                emit_text([f"Resolved: [{discussion_id}] {author}: {body_preview}"])
                resolved_count += 1
        elif is_bot and is_resolved:
            skipped_count += 1

    emit_text([f"Done: {resolved_count} threads resolved, {skipped_count} already resolved"])


# ---------- Argument Parsing ----------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage merge/pull requests across providers.")
    add_provider_args(parser)
    add_common_args(parser)

    subparsers = parser.add_subparsers(dest="command", required=True)

    create_p = subparsers.add_parser("create", help="Create a new MR/PR.")
    create_p.add_argument("--source", required=True, help="Source branch.")
    create_p.add_argument("--target", required=True, help="Target branch.")
    create_p.add_argument("--title", required=True, help="Title.")
    create_p.add_argument("--body", help="Description/body.")
    create_p.add_argument("--draft", action="store_true", help="Create as draft.")
    create_p.set_defaults(func=handle_create)

    merge_p = subparsers.add_parser("merge", help="Merge an MR/PR.")
    merge_p.add_argument("iid", type=int, help="MR IID or PR number.")
    merge_p.add_argument("--squash", action="store_true", help="Squash merge.")
    merge_p.add_argument("--delete-branch", action="store_true", help="Delete source branch after merge.")
    merge_p.add_argument("--message", help="Merge commit message.")
    merge_p.set_defaults(func=handle_merge)

    close_p = subparsers.add_parser("close", help="Close without merging.")
    close_p.add_argument("iid", type=int, help="MR IID or PR number.")
    close_p.add_argument("--comment", help="Optional closing comment.")
    close_p.set_defaults(func=handle_close)

    reopen_p = subparsers.add_parser("reopen", help="Reopen a closed MR/PR.")
    reopen_p.add_argument("iid", type=int, help="MR IID or PR number.")
    reopen_p.set_defaults(func=handle_reopen)

    comment_p = subparsers.add_parser("comment", help="Add a comment.")
    comment_p.add_argument("iid", type=int, help="MR IID or PR number.")
    comment_p.add_argument("--body", required=True, help="Comment text.")
    comment_p.set_defaults(func=handle_comment)

    list_p = subparsers.add_parser("list", help="List merge/pull requests.")
    list_p.add_argument(
        "--state",
        choices=["open", "merged", "closed", "all"],
        default="open",
        help="State filter.",
    )
    list_p.add_argument("--author", help="Filter by author username.")
    list_p.add_argument("--limit", type=int, default=20, help="Max items to return.")
    list_p.set_defaults(func=handle_list)

    get_p = subparsers.add_parser("get", help="Get a single MR/PR.")
    get_p.add_argument("iid", type=int, help="MR IID or PR number.")
    get_p.set_defaults(func=handle_get)

    notes_p = subparsers.add_parser("notes", help="Get MR/PR notes/comments.")
    notes_p.add_argument("iid", type=int, help="MR IID or PR number.")
    notes_p.add_argument("--author", help="Filter by author (case-insensitive substring match).")
    notes_p.add_argument("--full", action="store_true", help="Show full note bodies without truncation.")
    notes_p.add_argument("--limit", type=int, default=50, help="Max notes to return.")
    notes_p.set_defaults(func=handle_notes)

    resolve_p = subparsers.add_parser("resolve-threads", help="Resolve bot discussion threads (GitLab only).")
    resolve_p.add_argument("iid", type=int, help="MR IID.")
    resolve_p.add_argument("--author", help="Filter by author username (e.g., 'bot' to match bugbot).")
    resolve_p.set_defaults(func=handle_resolve_threads)

    return parser


# ---------- Main ----------

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    validate_provider_args(args)
    args.func(args)


if __name__ == "__main__":
    main()
