#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Fetch GitLab project info for procurement-web.

Outputs JSON summary to stdout.
Uses GITLAB_PERSONAL_ACCESS_TOKEN for authentication.

Usage:
    python fetch_project.py                # Get project info
    python fetch_project.py --branches     # List branches
    python fetch_project.py --tags         # List tags
    python fetch_project.py --members      # List project members
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from typing import Any

from gitlab_api import (
    perform_request,
    perform_request_list,
    print_json,
    project_api_url,
    require_token,
)


def summarize_project(project: dict[str, Any]) -> dict[str, Any]:
    """Extract key fields from project info."""
    return {
        "id": project.get("id"),
        "name": project.get("name"),
        "path_with_namespace": project.get("path_with_namespace"),
        "description": project.get("description"),
        "web_url": project.get("web_url"),
        "default_branch": project.get("default_branch"),
        "visibility": project.get("visibility"),
        "created_at": project.get("created_at"),
        "last_activity_at": project.get("last_activity_at"),
        "open_issues_count": project.get("open_issues_count"),
        "star_count": project.get("star_count"),
        "forks_count": project.get("forks_count"),
    }


def summarize_branch(branch: dict[str, Any]) -> dict[str, Any]:
    """Extract key fields from branch info."""
    commit = branch.get("commit", {})
    return {
        "name": branch.get("name"),
        "protected": branch.get("protected"),
        "default": branch.get("default"),
        "merged": branch.get("merged"),
        "commit_sha": commit.get("short_id"),
        "commit_title": commit.get("title"),
        "committed_date": commit.get("committed_date"),
    }


def summarize_tag(tag: dict[str, Any]) -> dict[str, Any]:
    """Extract key fields from tag info."""
    commit = tag.get("commit", {})
    return {
        "name": tag.get("name"),
        "message": tag.get("message"),
        "commit_sha": commit.get("short_id"),
        "committed_date": commit.get("committed_date"),
    }


def summarize_member(member: dict[str, Any]) -> dict[str, Any]:
    """Extract key fields from member info."""
    return {
        "id": member.get("id"),
        "username": member.get("username"),
        "name": member.get("name"),
        "access_level": member.get("access_level"),
        "state": member.get("state"),
    }


def fetch_project(token: str) -> dict[str, Any]:
    """Fetch project information."""
    return perform_request(project_api_url(), "GET", token)


def fetch_branches(token: str) -> list[dict[str, Any]]:
    """Fetch project branches."""
    url = f"{project_api_url()}/repository/branches"
    return perform_request_list(url, token)


def fetch_tags(token: str) -> list[dict[str, Any]]:
    """Fetch project tags."""
    url = f"{project_api_url()}/repository/tags"
    return perform_request_list(url, token)


def fetch_members(token: str) -> list[dict[str, Any]]:
    """Fetch project members."""
    url = f"{project_api_url()}/members"
    return perform_request_list(url, token)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch GitLab project info for procurement-web."
    )
    parser.add_argument("--branches", action="store_true", help="List branches")
    parser.add_argument("--tags", action="store_true", help="List tags")
    parser.add_argument("--members", action="store_true", help="List project members")
    return parser.parse_args()


def handle_branches(token: str) -> None:
    branches = fetch_branches(token)
    result = [summarize_branch(b) for b in branches]
    print_json({"branches": result})


def handle_tags(token: str) -> None:
    tags = fetch_tags(token)
    result = [summarize_tag(t) for t in tags]
    print_json({"tags": result})


def handle_members(token: str) -> None:
    members = fetch_members(token)
    result = [summarize_member(m) for m in members]
    print_json({"members": result})


def handle_project(token: str) -> None:
    project = fetch_project(token)
    print_json({"project": summarize_project(project)})


_FLAG_HANDLERS: list[tuple[str, Callable[[str], None]]] = [
    ("branches", handle_branches),
    ("tags", handle_tags),
    ("members", handle_members),
]


def main() -> None:
    args = parse_args()
    token = require_token()

    for flag, handler in _FLAG_HANDLERS:
        if getattr(args, flag):
            handler(token)
            return

    handle_project(token)


if __name__ == "__main__":
    main()
