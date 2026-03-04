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
import re
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


def issue_url(provider_name: str, project: str, iid: int | None, web_url: str | None) -> str:
    if web_url:
        return web_url
    if iid is None:
        return ""
    if provider_name == "github":
        return f"https://github.com/{project}/issues/{iid}"
    host = "gitlab.com" if provider_name == "gitlab" else "git.mt.gov"
    return f"https://{host}/{project}/-/issues/{iid}"


def parse_issue_ids(value: str | None) -> list[int]:
    if not value:
        return []
    entries = [part.strip() for part in value.split(",") if part.strip()]
    ids: list[int] = []
    for entry in entries:
        if not entry.isdigit():
            emit_error(f"Invalid issue id '{entry}'. Use numeric IDs.")
        num = int(entry)
        if num <= 0:
            emit_error("Issue IDs must be positive.")
        ids.append(num)
    return ids


def provider_for(name: str, project: str | None, token: str | None, verbose: bool) -> Any:
    return get_provider(name, project=project, token=token, verbose=verbose)


# ---------------------------------------------------------------------------
# Mirror logic
# ---------------------------------------------------------------------------


def fetch_issue(provider: Any, provider_name: str, project: str, iid: int) -> dict[str, Any]:
    if provider_name == "github":
        result = provider.request("GET", f"/repos/{project}/issues/{iid}")
        data = ensure_ok_dict(result, "Fetch GitHub issue")
        if "pull_request" in data:
            emit_error(f"Item #{iid} is a pull request, not an issue.")
        return data
    endpoint = f"/projects/{{project}}/issues/{iid}"
    result = provider.request("GET", endpoint)
    return ensure_ok_dict(result, "Fetch GitLab issue")


def list_source_issues(provider: Any, provider_name: str, project: str, limit: int) -> list[int]:
    if provider_name == "github":
        result = provider.request(
            "GET",
            f"/repos/{project}/issues",
            params={"state": "open", "per_page": str(min(limit, 100))},
        )
        data = ensure_ok_list(result, "List GitHub issues")
        ids: list[int] = []
        for item in data:
            if "pull_request" in item:
                continue
            if isinstance(item.get("number"), int):
                ids.append(int(item["number"]))
            if len(ids) >= limit:
                break
        return ids

    result = provider.request(
        "GET",
        "/projects/{project}/issues",
        params={"state": "opened", "per_page": str(min(limit, 100))},
    )
    data = ensure_ok_list(result, "List GitLab issues")
    return [int(item["iid"]) for item in data[:limit] if isinstance(item.get("iid"), int)]


def normalize_labels(provider_name: str, labels: list[str]) -> Any:
    if provider_name == "github":
        return labels
    return ",".join(labels) if labels else ""


def create_target_issue(
    provider: Any,
    provider_name: str,
    project: str,
    title: str,
    body: str,
    labels: list[str],
    dry_run: bool,
) -> str:
    if dry_run:
        emit_text([f"[dry-run] mirror -> {project}", f"title={title}", f"labels={labels}"])
        return ""

    if provider_name == "github":
        payload: dict[str, Any] = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels
        result = provider.request("POST", f"/repos/{project}/issues", json=payload)
        data = ensure_ok_dict(result, "Create GitHub issue")
        return data.get("html_url") or ""

    payload = {"title": title, "description": body}
    if labels:
        payload["labels"] = normalize_labels(provider_name, labels)
    result = provider.request("POST", "/projects/{project}/issues", json=payload)
    data = ensure_ok_dict(result, "Create GitLab issue")
    return data.get("web_url") or ""


def comment_source(provider: Any, provider_name: str, project: str, iid: int, body: str, dry_run: bool) -> None:
    if dry_run:
        emit_text([f"[dry-run] comment on {project}#{iid}: {truncate(body, 200)}"])
        return
    if provider_name == "github":
        endpoint = f"/repos/{project}/issues/{iid}/comments"
        provider.request("POST", endpoint, json={"body": body})
    else:
        endpoint = f"/projects/{{project}}/issues/{iid}/notes"
        provider.request("POST", endpoint, json={"body": body})


def handle_mirror(args: argparse.Namespace) -> None:
    src_token = args.source_token or args.token
    tgt_token = args.target_token or args.token

    src_provider = provider_for(args.source, args.source_project or args.project, src_token, args.verbose)
    tgt_provider = provider_for(args.target, args.target_project, tgt_token, args.verbose)

    src_project = ensure_project(src_provider)
    tgt_project = ensure_project(tgt_provider)

    issue_ids = parse_issue_ids(args.issues)
    if not issue_ids:
        issue_ids = list_source_issues(src_provider, args.source, src_project, limit=20)
    if not issue_ids:
        emit_text(["No source issues to mirror."])
        return

    results: list[str] = []
    for iid in issue_ids:
        source_issue = fetch_issue(src_provider, args.source, src_project, iid)
        labels = [lbl.get("name", lbl) if isinstance(lbl, dict) else lbl for lbl in source_issue.get("labels", [])]
        title = source_issue.get("title") or "Untitled"
        source_url = issue_url(args.source, src_project, source_issue.get("iid") or source_issue.get("number"), source_issue.get("web_url") or source_issue.get("html_url"))
        body = source_issue.get("description") or source_issue.get("body") or ""
        mirror_body = "\n\n".join([body, f"Mirrored from {source_url}"]).strip()

        target_url = create_target_issue(
            tgt_provider,
            args.target,
            tgt_project,
            title,
            mirror_body,
            labels,
            args.dry_run,
        )

        if target_url:
            comment_source(
                src_provider,
                args.source,
                src_project,
                iid,
                f"Mirrored to {target_url}",
                args.dry_run,
            )
            results.append(f"{source_url} -> {target_url}")
        else:
            results.append(f"{source_url} mirrored (dry-run)")

    emit_text(results)


# ---------------------------------------------------------------------------
# Backlog (lightweight listing for now)
# ---------------------------------------------------------------------------


def handle_backlog(args: argparse.Namespace) -> None:
    provider = get_provider(
        args.provider,
        project=args.project,
        token=getattr(args, "token", None),
        verbose=args.verbose,
    )
    project = ensure_project(provider)
    group_path = project.rsplit("/", 1)[0] if "/" in project else project
    if args.epic:
        endpoint = f"/groups/{group_path}/epics/{args.epic}"
        result = provider.request("GET", endpoint)
        data = ensure_ok_dict(result, "Get epic")
        emit_markdown(
            "\n".join(
                [
                    f"**!{data.get('iid')}: {data.get('title','')}**",
                    f"- state: {data.get('state')}",
                    f"- url: {data.get('web_url')}",
                    "",
                    truncate(data.get("description") or "", 1500),
                ]
            )
        )
        return

    result = provider.request(
        "GET",
        f"/groups/{group_path}/epics",
        params={"state": "opened", "per_page": "50", "sort": "desc"},
    )
    epics = ensure_ok_list(result, "List epics")
    lines = [f"!{e.get('iid')}: {truncate(e.get('title') or '', 120)} {e.get('web_url','')}" for e in epics]
    lines.append("(No seed backlog issues defined; add backlog data before syncing.)")
    emit_text(lines or ["(no epics)"])


# ---------------------------------------------------------------------------
# Cross-reference patching
# ---------------------------------------------------------------------------


def rewrite_description(text: str, project: str, provider_name: str) -> tuple[str, int]:
    host = "gitlab.com" if provider_name == "gitlab" else "git.mt.gov"
    pattern = re.compile(rf"{re.escape(project)}#(\d+)")
    replacement = f"https://{host}/{project}/-/issues/\\1"
    new_text, count = pattern.subn(replacement, text)
    return new_text, count


def handle_crossrefs(args: argparse.Namespace) -> None:
    provider = get_provider(
        args.provider,
        project=args.project,
        token=getattr(args, "token", None),
        verbose=args.verbose,
    )
    if args.provider == "github":
        emit_error("crossrefs is supported for gitlab/state providers only.")

    project = ensure_project(provider)
    issue_ids = parse_issue_ids(args.issues)
    if not issue_ids:
        emit_error("--issues is required for crossrefs.")

    results: list[str] = []
    for iid in issue_ids:
        endpoint = f"/projects/{{project}}/issues/{iid}"
        fetched = provider.request("GET", endpoint)
        issue = ensure_ok_dict(fetched, "Fetch issue")
        description = issue.get("description") or ""
        updated, count = rewrite_description(description, project, args.provider)
        if count == 0:
            results.append(f"{iid}: no changes")
            continue
        if args.dry_run:
            results.append(f"[dry-run] {iid}: {count} replacements")
            continue
        update_result = provider.request("PUT", endpoint, json={"description": updated})
        ensure_ok_dict(update_result, "Update issue description")
        results.append(f"{iid}: updated ({count} replacements)")

    emit_text(results)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cross-platform git sync utilities.")
    add_provider_args(parser)
    add_common_args(parser)
    subs = parser.add_subparsers(dest="command", required=True)

    p_mirror = subs.add_parser("mirror", help="Mirror issues between providers.")
    p_mirror.add_argument("--source", choices=["gitlab", "github", "state"], required=True)
    p_mirror.add_argument("--target", choices=["gitlab", "github", "state"], required=True)
    p_mirror.add_argument("--source-project", help="Source project path/id (defaults to env for source).")
    p_mirror.add_argument("--target-project", help="Target project path/id (defaults to env for target).")
    p_mirror.add_argument("--issues", help="Comma-separated issue ids to mirror. Defaults to recent open issues.")
    p_mirror.add_argument(
        "--source-token",
        help="Token for the source provider (defaults to --token or env).",
    )
    p_mirror.add_argument(
        "--target-token",
        help="Token for the target provider (defaults to --token or env).",
    )

    p_backlog = subs.add_parser("backlog", help="Inspect/sync backlog epics.")
    p_backlog.add_argument("--epic", type=int, help="Epic IID to display.")

    p_cross = subs.add_parser("crossrefs", help="Patch cross-references in issue descriptions.")
    p_cross.add_argument("--issues", required=True, help="Comma-separated issue IDs to patch.")

    return parser


def _cmd_mirror(args: argparse.Namespace) -> None:
    handle_mirror(args)


def _cmd_backlog(args: argparse.Namespace) -> None:
    handle_backlog(args)


def _cmd_crossrefs(args: argparse.Namespace) -> None:
    handle_crossrefs(args)


_COMMANDS: dict[str, Callable[[argparse.Namespace], None]] = {
    "mirror": _cmd_mirror,
    "backlog": _cmd_backlog,
    "crossrefs": _cmd_crossrefs,
}


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    validate_provider_args(args)

    handler = _COMMANDS.get(args.command)
    if handler is None:
        parser.error(f"Unknown command: {args.command}")
    handler(args)


if __name__ == "__main__":
    main()
