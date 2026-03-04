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


def render_info(provider_name: str, data: dict[str, Any]) -> None:
    if provider_name in ("gitlab", "state"):
        lines = [
            f"**{data.get('name')}** ({data.get('path_with_namespace')})",
            f"- url: {data.get('web_url')}",
            f"- default_branch: {data.get('default_branch')}",
            f"- visibility: {data.get('visibility')}",
            f"- open_issues: {data.get('open_issues_count')}",
            f"- stars: {data.get('star_count')} forks: {data.get('forks_count')}",
            "",
            truncate(data.get("description") or "", 1000),
        ]
    else:
        lines = [
            f"**{data.get('full_name')}**",
            f"- url: {data.get('html_url')}",
            f"- default_branch: {data.get('default_branch')}",
            f"- visibility: {'private' if data.get('private') else 'public'}",
            f"- open_issues: {data.get('open_issues_count')}",
            f"- stars: {data.get('stargazers_count')} forks: {data.get('forks_count')}",
            "",
            truncate(data.get("description") or "", 1000),
        ]
    emit_markdown("\n".join(lines))


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------


def op_info(provider: Any, provider_name: str) -> None:
    project = ensure_project(provider)
    endpoint = f"/repos/{project}" if provider_name == "github" else "/projects/{project}"
    result = provider.request("GET", endpoint)
    data = ensure_ok_dict(result, "Fetch project info")
    render_info(provider_name, data)


def op_branches(provider: Any, provider_name: str, search: str | None) -> None:
    project = ensure_project(provider)
    if provider_name in ("gitlab", "state"):
        params = {"per_page": "100"}
        if search:
            params["search"] = search
        result = provider.request("GET", "/projects/{project}/repository/branches", params=params)
    else:
        result = provider.request("GET", f"/repos/{project}/branches", params={"per_page": "100"})
    branches = ensure_ok_list(result, "List branches")
    lines = []
    for br in branches:
        name = br.get("name") or ""
        if search and provider_name == "github" and search.lower() not in name.lower():
            continue
        commit = br.get("commit") or {}
        sha = commit.get("sha") or commit.get("short_id") or ""
        lines.append(f"- {name} {sha[:8]}")
    emit_text(lines or ["(no branches)"])


def op_members(provider: Any, provider_name: str, access_level: str | None) -> None:
    project = ensure_project(provider)
    if provider_name in ("gitlab", "state"):
        endpoint = "/projects/{project}/members/all"
        result = provider.request("GET", endpoint, params={"per_page": "100"})
        members = ensure_ok_list(result, "List members")
        lines = []
        threshold = 0
        if access_level == "maintainer":
            threshold = 40
        elif access_level == "developer":
            threshold = 30
        for m in members:
            level = m.get("access_level") or 0
            if threshold and level < threshold:
                continue
            lines.append(
                f"- {m.get('username')} ({m.get('name')}) level={level} state={m.get('state')}"
            )
        emit_text(lines or ["(no members)"])
    else:
        perm = None
        if access_level == "maintainer":
            perm = "maintain"
        elif access_level == "developer":
            perm = "push"
        params = {"per_page": "100"}
        if perm:
            params["permission"] = perm
        endpoint = f"/repos/{project}/collaborators"
        result = provider.request("GET", endpoint, params=params)
        members = ensure_ok_list(result, "List collaborators")
        lines = []
        for m in members:
            login = m.get("login") or ""
            perm_info = m.get("permissions") or {}
            perms = ",".join([k for k, v in perm_info.items() if v])
            lines.append(f"- {login} permissions={perms}")
        emit_text(lines or ["(no collaborators)"])


def _resolve_gitlab_namespace_id(provider: Any, group_path: str) -> int:
    encoded = urllib.parse.quote(group_path, safe="")
    result = provider.request("GET", f"/groups/{encoded}")
    data = ensure_ok_dict(result, f"Resolve group '{group_path}'")
    ns_id = data.get("id")
    if not isinstance(ns_id, int):
        emit_error(f"Group '{group_path}' returned no numeric ID.")
    return ns_id


def op_create(
    provider: Any,
    provider_name: str,
    name: str,
    group: str | None,
    visibility: str,
    description: str | None,
    dry_run: bool,
) -> None:
    if provider_name in ("gitlab", "state"):
        body: dict[str, Any] = {
            "name": name,
            "path": name,
            "visibility": visibility,
            "initialize_with_readme": False,
        }
        if description:
            body["description"] = description
        if group:
            body["namespace_id"] = _resolve_gitlab_namespace_id(provider, group)

        if dry_run:
            emit_text([f"Would create project '{name}' on {provider_name}", f"  payload: {body}"])
            return

        result = provider.request("POST", "/projects", json=body)
        data = ensure_ok_dict(result, "Create project")
        lines = [
            f"Created **{data.get('path_with_namespace')}**",
            f"- url: {data.get('web_url')}",
            f"- ssh: {data.get('ssh_url_to_repo')}",
            f"- http: {data.get('http_url_to_repo')}",
            f"- id: {data.get('id')}",
            f"- visibility: {data.get('visibility')}",
        ]
        emit_markdown("\n".join(lines))
    else:
        body_gh: dict[str, Any] = {
            "name": name,
            "private": visibility == "private",
            "auto_init": False,
        }
        if description:
            body_gh["description"] = description

        endpoint = f"/orgs/{group}/repos" if group else "/user/repos"

        if dry_run:
            emit_text([f"Would create repo '{name}' on github", f"  endpoint: {endpoint}", f"  payload: {body_gh}"])
            return

        result = provider.request("POST", endpoint, json=body_gh)
        data = ensure_ok_dict(result, "Create repository")
        lines = [
            f"Created **{data.get('full_name')}**",
            f"- url: {data.get('html_url')}",
            f"- ssh: {data.get('ssh_url')}",
            f"- http: {data.get('clone_url')}",
            f"- id: {data.get('id')}",
            f"- visibility: {'private' if data.get('private') else 'public'}",
        ]
        emit_markdown("\n".join(lines))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Query project metadata.")
    add_provider_args(parser)
    add_common_args(parser)

    subs = parser.add_subparsers(dest="command", required=True)

    subs.add_parser("info", help="Project summary.")

    p_branches = subs.add_parser("branches", help="List branches.")
    p_branches.add_argument("--search", help="Substring filter for branch name.")

    p_members = subs.add_parser("members", help="List members/collaborators.")
    p_members.add_argument(
        "--access-level",
        choices=["maintainer", "developer"],
        help="Filter by access/permission level.",
    )

    p_create = subs.add_parser("create", help="Create a new project/repository.")
    p_create.add_argument("--name", required=True, help="Repository name (used as path slug).")
    p_create.add_argument("--group", help="Group/namespace (GitLab) or organization (GitHub).")
    p_create.add_argument(
        "--visibility",
        choices=["private", "internal", "public"],
        default="private",
        help="Repository visibility (default: private).",
    )
    p_create.add_argument("--description", help="Repository description.")

    return parser


def _cmd_info(provider: Any, provider_name: str, args: argparse.Namespace) -> None:
    del args
    op_info(provider, provider_name)


def _cmd_branches(provider: Any, provider_name: str, args: argparse.Namespace) -> None:
    op_branches(provider, provider_name, args.search)


def _cmd_members(provider: Any, provider_name: str, args: argparse.Namespace) -> None:
    op_members(provider, provider_name, args.access_level)


def _cmd_create(provider: Any, provider_name: str, args: argparse.Namespace) -> None:
    op_create(provider, provider_name, args.name, args.group, args.visibility, args.description, args.dry_run)


_COMMANDS: dict[str, Callable[[Any, str, argparse.Namespace], None]] = {
    "info": _cmd_info,
    "branches": _cmd_branches,
    "members": _cmd_members,
    "create": _cmd_create,
}


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command != "create":
        validate_provider_args(args)

    provider = get_provider(
        args.provider,
        project=getattr(args, "project", None),
        token=getattr(args, "token", None),
        verbose=args.verbose,
    )

    handler = _COMMANDS.get(args.command)
    if handler is None:
        parser.error(f"Unknown command: {args.command}")
    handler(provider, args.provider, args)


if __name__ == "__main__":
    main()
