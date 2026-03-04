#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = ["python-dotenv>=1.0"]
# ///
"""
GitLab epic/issue helper for procurement-web.

Supports:
- Creating an epic in the project namespace group
- Creating an issue in the project
- Linking an issue to an epic

Environment:
- GITLAB_PERSONAL_ACCESS_TOKEN (required)
- GITLAB_PROJECT_ID (required) - e.g., "cdo-office/procurement-web"
- GITLAB_BASE_URL (optional; default: https://gitlab.com)

Note: This script is in git-workflows/ for GitHub/GitLab migration tasks.
For general GitLab operations, prefer gitlab-workflows/ which has a shared
gitlab_api.py module.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def load_env_if_available() -> None:
    """Load .env file if python-dotenv is available. Silent no-op otherwise."""
    try:
        from dotenv import find_dotenv, load_dotenv

        # Try cwd first, then script location
        env_path = find_dotenv(usecwd=True)
        if env_path:
            load_dotenv(env_path, override=not os.environ.get("GITLAB_PERSONAL_ACCESS_TOKEN"))
            return

        env_path = find_dotenv(usecwd=False)
        if env_path:
            load_dotenv(env_path, override=not os.environ.get("GITLAB_PERSONAL_ACCESS_TOKEN"))
            return

        # Fallback: walk up from script location
        for parent in Path(__file__).resolve().parents:
            candidate = parent / ".env"
            if candidate.exists():
                load_dotenv(candidate, override=not os.environ.get("GITLAB_PERSONAL_ACCESS_TOKEN"))
                return
    except ImportError:
        # Optional dependency; ignore if not present.
        pass


load_env_if_available()


DEFAULT_BASE_URL = "https://gitlab.com"
# Use same env var as gitlab-workflows/ for consistency
TOKEN_ENV_VAR = "GITLAB_PERSONAL_ACCESS_TOKEN"
PROJECT_ENV_VAR = "GITLAB_PROJECT_ID"
BASE_URL_ENV_VAR = "GITLAB_BASE_URL"


@dataclass(frozen=True)
class ProjectContext:
    base_url: str
    project_id: str
    group_id: str


def require_env(name: str, fallback: str | None = None) -> str:
    value = os.environ.get(name) or fallback
    if not value:
        raise SystemExit(f"{name} is required")
    return value


def build_headers(token: str) -> dict[str, str]:
    return {
        "PRIVATE-TOKEN": token,
        "Content-Type": "application/json",
        "User-Agent": "gitlab-issues-script",
    }


def http_request(
    method: str,
    url: str,
    token: str,
    payload: dict[str, Any] | None = None,
    allow_conflict: bool = False,
) -> dict[str, Any]:
    """
    Perform HTTP request to GitLab API.

    Args:
        allow_conflict: If True, 409 Conflict returns {"conflict": True} instead of exiting.
    """
    data = json.dumps(payload or {}).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(url, data=data, method=method, headers=build_headers(token))
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode()
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as error:
        detail = error.read().decode() if error.fp else error.reason
        if allow_conflict and error.code == 409:
            return {"conflict": True, "message": detail}
        sys.stderr.write(f"GitLab API error {error.code}: {detail}\n")
        raise SystemExit(1) from error


def fetch_project(base_url: str, project_id: str, token: str) -> dict[str, Any]:
    encoded_id = urllib.parse.quote_plus(project_id)
    url = f"{base_url}/api/v4/projects/{encoded_id}"
    return http_request("GET", url, token)


def resolve_group_id(base_url: str, project_id: str, token: str) -> str:
    project = fetch_project(base_url, project_id, token)
    namespace = project.get("namespace") or {}
    group_id = namespace.get("id")
    kind = namespace.get("kind")
    if not group_id or kind != "group":
        raise SystemExit("Group namespace is required to create epics. Provide --group-id explicitly if needed.")
    return str(group_id)


def create_epic(base_url: str, group_id: str, token: str, title: str, description: str, labels: list[str]) -> dict[str, Any]:
    url = f"{base_url}/api/v4/groups/{group_id}/epics"
    payload = {
        "title": title,
        "description": description,
        "labels": ",".join(labels) if labels else None,
    }
    return http_request("POST", url, token, payload)


def create_issue(base_url: str, project_id: str, token: str, title: str, description: str, labels: list[str]) -> dict[str, Any]:
    url = f"{base_url}/api/v4/projects/{urllib.parse.quote_plus(project_id)}/issues"
    payload = {
        "title": title,
        "description": description,
        "labels": ",".join(labels) if labels else None,
    }
    return http_request("POST", url, token, payload)


def link_issue_to_epic(base_url: str, group_id: str, epic_iid: int, issue_id: int, token: str) -> dict[str, Any]:
    """
    Link an issue to an epic.

    GitLab API: POST /groups/:id/epics/:epic_iid/issues/:issue_id
    Note: issue_id is in the URL path, NOT the request body.

    Returns {"conflict": True} if issue is already linked (409).
    """
    url = f"{base_url}/api/v4/groups/{group_id}/epics/{epic_iid}/issues/{issue_id}"
    return http_request("POST", url, token, allow_conflict=True)


def parse_labels(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [label.strip() for label in raw.split(",") if label.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create GitLab epics/issues and link them.")
    parser.add_argument("--project-id", type=str, help="GitLab project ID (required; uses GITLAB_PROJECT_ID from .env if not passed)")
    parser.add_argument("--group-id", type=str, help="GitLab group ID for epics (derived from project namespace if absent)")
    parser.add_argument("--base-url", type=str, default=None, help="GitLab base URL (default: https://gitlab.com)")
    parser.add_argument("--action", type=str, required=True, choices=["create-epic", "create-issue", "link"], help="Action to perform")
    parser.add_argument("--title", type=str, help="Title for epic/issue")
    parser.add_argument("--description", type=str, default="", help="Description/markdown body")
    parser.add_argument("--labels", type=str, help="Comma-separated labels")
    parser.add_argument("--epic-iid", type=int, help="Epic IID (for linking or issue creation + link)")
    parser.add_argument("--issue-id", type=int, help="Issue ID (for linking to epic)")
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if args.action in {"create-epic", "create-issue"} and not args.title:
        raise SystemExit("--title is required for create-epic/create-issue")
    if args.action == "link" and (args.issue_id is None or args.epic_iid is None):
        raise SystemExit("--issue-id and --epic-iid are required for link action")


def main() -> None:
    args = parse_args()
    validate_args(args)

    token = require_env(TOKEN_ENV_VAR)
    base_url = args.base_url or os.environ.get(BASE_URL_ENV_VAR) or DEFAULT_BASE_URL
    project_id = args.project_id or os.environ.get(PROJECT_ENV_VAR)
    if not project_id:
        raise SystemExit(f"{PROJECT_ENV_VAR} is required (set in .env or pass --project-id)")

    labels = parse_labels(args.labels)

    if args.action == "create-epic":
        group_id = args.group_id or resolve_group_id(base_url, project_id, token)
        epic = create_epic(base_url, group_id, token, args.title, args.description, labels)
        output = {"success": True, "epic": epic}
        print(json.dumps(output, indent=2))
        return

    if args.action == "create-issue":
        issue = create_issue(base_url, project_id, token, args.title, args.description, labels)
        epic_iid = args.epic_iid
        group_id = args.group_id
        if epic_iid is not None:
            group_value = group_id or resolve_group_id(base_url, project_id, token)
            linked = link_issue_to_epic(base_url, group_value, epic_iid, issue_id=int(issue["id"]), token=token)
            issue["epic_link"] = linked
        output = {"success": True, "issue": issue}
        print(json.dumps(output, indent=2))
        return

    if args.action == "link":
        group_id = args.group_id or resolve_group_id(base_url, project_id, token)
        linked = link_issue_to_epic(base_url, group_id, args.epic_iid, args.issue_id, token)
        output = {"success": True, "link": linked}
        print(json.dumps(output, indent=2))
        return

    raise SystemExit("Unsupported action")


if __name__ == "__main__":
    main()
