#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Fetch GitLab milestones for procurement-web.

Outputs JSON summary to stdout.
Uses GITLAB_PERSONAL_ACCESS_TOKEN for authentication.

Usage:
    python fetch_milestones.py                    # List active milestones
    python fetch_milestones.py --state closed     # List closed milestones
    python fetch_milestones.py --milestone 1      # Fetch single milestone
"""

from __future__ import annotations

import argparse
from typing import Any

from gitlab_api import (
    milestones_api_url,
    perform_request,
    perform_request_list,
    print_json,
    require_token,
)


def summarize_milestone(milestone: dict[str, Any]) -> dict[str, Any]:
    """Extract key fields from milestone info."""
    return {
        "id": milestone.get("id"),
        "iid": milestone.get("iid"),
        "title": milestone.get("title"),
        "description": milestone.get("description"),
        "state": milestone.get("state"),
        "due_date": milestone.get("due_date"),
        "start_date": milestone.get("start_date"),
        "web_url": milestone.get("web_url"),
        "created_at": milestone.get("created_at"),
        "updated_at": milestone.get("updated_at"),
    }


def fetch_single_milestone(token: str, milestone_id: int) -> dict[str, Any]:
    """Fetch a single milestone by ID."""
    url = f"{milestones_api_url()}/{milestone_id}"
    return perform_request(url, "GET", token)


def fetch_milestone_list(
    token: str,
    state: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    """
    Fetch list of milestones.

    GitLab milestone states: active, closed
    """
    params = {
        "per_page": str(min(limit, 100)),
    }
    if state:
        params["state"] = state

    milestones = perform_request_list(milestones_api_url(), token, params)
    return milestones[:limit]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch GitLab milestones for procurement-web."
    )
    parser.add_argument(
        "--state",
        type=str,
        choices=["active", "closed"],
        help="Milestone state filter",
    )
    parser.add_argument("--milestone", type=int, help="Fetch single milestone by ID")
    parser.add_argument(
        "--limit", type=int, default=20, help="Max milestones to return"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    token = require_token()

    if args.milestone:
        milestone = fetch_single_milestone(token, args.milestone)
        print_json({"milestones": [summarize_milestone(milestone)]})
    else:
        milestones = fetch_milestone_list(token, args.state, args.limit)
        result = [summarize_milestone(m) for m in milestones]
        print_json({"milestones": result})


if __name__ == "__main__":
    main()
