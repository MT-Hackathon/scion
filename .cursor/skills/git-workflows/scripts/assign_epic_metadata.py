#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Bulk assign epic labels and milestones to GitLab issues.

Standard usage:
uv run .cursor/skills/git-workflows/scripts/assign_epic_metadata.py --epic 1 --milestone-id 6281079 --issues "95"
"""
from __future__ import annotations

import argparse
from typing import Iterable

from gitlab_api import (
    issues_api_url,
    perform_request,
    print_json,
    require_token,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Apply an epic label and milestone to a set of GitLab issues."
    )
    parser.add_argument(
        "--epic",
        type=int,
        required=True,
        help="Epic number to label issues with (adds label epic::<N>)",
    )
    parser.add_argument(
        "--issues",
        type=str,
        required=True,
        help="Comma-separated list of issue IIDs",
    )
    parser.add_argument(
        "--milestone-id",
        type=int,
        required=True,
        help="Milestone ID to assign each issue",
    )
    return parser.parse_args()


def parse_iids(raw: str) -> list[int]:
    """
    Parse a comma separated list of issue IIDs.
    """
    issues: list[int] = []
    for segment in raw.split(","):
        candidate = segment.strip()
        if not candidate:
            continue
        try:
            iid = int(candidate)
        except ValueError as exc:
            raise SystemExit(f"Invalid issue IID '{candidate}': {exc}") from exc
        if iid <= 0:
            raise SystemExit(f"Issue IID must be positive: {iid}")
        issues.append(iid)
    if not issues:
        raise SystemExit("At least one issue IID is required.")
    return issues


def assign_epic_to_issue(
    token: str,
    iid: int,
    epic: int,
    milestone_id: int,
) -> dict[str, int | str | None]:
    """
    Submit a PUT request to update the issue with the epic label and milestone.
    """
    url = f"{issues_api_url()}/{iid}"
    payload = {"add_labels": f"epic::{epic}", "milestone_id": milestone_id}
    response = perform_request(url, "PUT", token, payload)
    return {
        "iid": iid,
        "epic_label": f"epic::{epic}",
        "milestone_id": milestone_id,
        "web_url": response.get("web_url"),
    }


def main() -> None:
    args = parse_args()
    iids = parse_iids(args.issues)
    token = require_token()
    results: list[dict[str, int | str | None]] = []

    for iid in iids:
        result = assign_epic_to_issue(token, iid, args.epic, args.milestone_id)
        results.append(result)

    print_json(results)


if __name__ == "__main__":
    main()
