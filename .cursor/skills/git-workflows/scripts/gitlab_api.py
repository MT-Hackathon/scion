#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = ["python-dotenv>=1.0"]
# ///
"""
GitLab API shared module for procurement-web workflow scripts.

All GitLab workflow scripts import from this module.
Uses GITLAB_PERSONAL_ACCESS_TOKEN from .env via python-dotenv.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_PATH = "cdo-office/procurement-web"
PROJECT_PATH_ENCODED = urllib.parse.quote(PROJECT_PATH, safe="")
API_BASE = "https://gitlab.com/api/v4"
TOKEN_ENV_VAR = "GITLAB_PERSONAL_ACCESS_TOKEN"


# ---------------------------------------------------------------------------
# Environment Loading
# ---------------------------------------------------------------------------

def find_env_path(start: Path) -> Path | None:
    """Search for .env file from start directory up to filesystem root."""
    for parent in (start, *start.parents):
        candidate = parent / ".env"
        if candidate.exists():
            return candidate
    return None


def load_env_if_available() -> None:
    """Load .env file if python-dotenv is available. Silent no-op otherwise.

    Searches from both the script directory and the current working directory,
    loading the first .env file found.
    """
    try:
        from dotenv import find_dotenv, load_dotenv

        env_path = find_dotenv(usecwd=True)
        if env_path:
            load_dotenv(env_path, override=not os.environ.get(TOKEN_ENV_VAR))
            return

        env_path = find_dotenv(usecwd=False)
        if env_path:
            load_dotenv(env_path, override=not os.environ.get(TOKEN_ENV_VAR))
            return

        script_root = Path(__file__).resolve().parent
        cwd_root = Path.cwd().resolve()
        searched: set[Path] = set()

        for root in (script_root, cwd_root):
            if root in searched:
                continue
            searched.add(root)
            env_path = find_env_path(root)
            if env_path:
                load_dotenv(env_path)
                return
    except ImportError:
        pass


load_env_if_available()


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

def require_token() -> str:
    """Return GitLab token from environment or exit with error."""
    token = os.environ.get(TOKEN_ENV_VAR)
    if not token:
        raise SystemExit(f"{TOKEN_ENV_VAR} is required")
    return token


def build_headers(token: str) -> dict[str, str]:
    """Build HTTP headers for GitLab API requests."""
    return {
        "PRIVATE-TOKEN": token,
        "Content-Type": "application/json",
        "User-Agent": "procurement-web-gitlab-scripts",
    }


# ---------------------------------------------------------------------------
# URL Builders
# ---------------------------------------------------------------------------

def encode_project_path(project_path: str | None = None) -> str:
    """Return a URL-encoded project path (defaults to configured project)."""
    if project_path is None:
        return PROJECT_PATH_ENCODED
    return urllib.parse.quote(project_path, safe="")


def project_api_url(project_path: str | None = None) -> str:
    """Return the base API URL for the project."""
    encoded = encode_project_path(project_path)
    return f"{API_BASE}/projects/{encoded}"


def issues_api_url(project_path: str | None = None) -> str:
    """Return the issues API URL for the project."""
    return f"{project_api_url(project_path)}/issues"


def merge_requests_api_url(project_path: str | None = None) -> str:
    """Return the merge requests API URL for the project."""
    return f"{project_api_url(project_path)}/merge_requests"


def pipelines_api_url(project_path: str | None = None) -> str:
    """Return the pipelines API URL for the project."""
    return f"{project_api_url(project_path)}/pipelines"


def labels_api_url(project_path: str | None = None) -> str:
    """Return the labels API URL for the project."""
    return f"{project_api_url(project_path)}/labels"


def milestones_api_url(project_path: str | None = None) -> str:
    """Return the milestones API URL for the project."""
    return f"{project_api_url(project_path)}/milestones"


# ---------------------------------------------------------------------------
# HTTP Request Helper
# ---------------------------------------------------------------------------

def perform_request(
    url: str,
    method: str,
    token: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Perform an HTTP request to the GitLab API.

    Args:
        url: Full API URL
        method: HTTP method (GET, POST, PUT, DELETE)
        token: GitLab personal access token
        payload: Optional JSON payload for POST/PUT

    Returns:
        Parsed JSON response as dict

    Raises:
        SystemExit: On HTTP error with details printed to stderr
    """
    headers = build_headers(token)
    data = json.dumps(payload).encode("utf-8") if payload else None

    request = urllib.request.Request(url, data=data, method=method, headers=headers)

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode()
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as error:
        detail = error.read().decode() if error.fp else error.reason
        sys.stderr.write(f"GitLab API error {error.code}: {detail}\n")
        raise SystemExit(1) from error


def perform_request_list(
    url: str,
    token: str,
    params: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """
    Perform a GET request expecting a list response.

    Args:
        url: Base API URL (query params will be appended)
        token: GitLab personal access token
        params: Optional query parameters

    Returns:
        List of parsed JSON objects
    """
    if params:
        query = urllib.parse.urlencode({k: v for k, v in params.items() if v})
        url = f"{url}?{query}"

    headers = build_headers(token)
    request = urllib.request.Request(url, method="GET", headers=headers)

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode()
            return json.loads(body) if body else []
    except urllib.error.HTTPError as error:
        detail = error.read().decode() if error.fp else error.reason
        sys.stderr.write(f"GitLab API error {error.code}: {detail}\n")
        raise SystemExit(1) from error


# ---------------------------------------------------------------------------
# Output Helpers
# ---------------------------------------------------------------------------

def print_json(data: Any) -> None:
    """Print data as formatted JSON to stdout."""
    print(json.dumps(data, indent=2))


def print_compact_json(data: Any) -> None:
    """Print data as compact JSON to stdout."""
    print(json.dumps(data, separators=(",", ":")))
