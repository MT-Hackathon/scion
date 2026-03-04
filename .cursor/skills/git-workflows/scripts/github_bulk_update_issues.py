#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = ["python-dotenv>=1.0"]
# ///
"""
Bulk update/create GitHub issues from markdown files containing JSON payloads.

Parses markdown files with embedded JSON issue definitions and executes
GitHub API calls to update or create issues.

Relies on GITHUB_PERSONAL_ACCESS_TOKEN for authentication.

Usage:
    python github_bulk_update_issues.py --file path/to/issues.md
    python github_bulk_update_issues.py --file issues.md --dry-run
    python github_bulk_update_issues.py --file refined.md --file new.md
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def _load_env_file(env_path: Path) -> None:
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        os.environ.setdefault(name.strip(), value.strip().strip('"').strip("'"))


def load_env_if_available() -> None:
    """Load .env file if python-dotenv is available. Silent no-op otherwise."""
    env_path = Path(__file__).resolve().parents[4] / ".env"
    if not env_path.exists():
        return

    try:
        from dotenv import load_dotenv

        load_dotenv(env_path)
    except ImportError:
        _load_env_file(env_path)


load_env_if_available()

sys.path.append(str(Path(__file__).resolve().parent))

from github_fetch_issues import API, TOKEN_ENV_VAR, build_headers, require_token  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bulk update/create GitHub issues from markdown files."
    )
    parser.add_argument(
        "--file",
        type=str,
        action="append",
        required=True,
        help="Markdown file(s) containing issue JSON payloads",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and validate without making API calls",
    )
    parser.add_argument(
        "--start",
        type=int,
        default=1,
        help="Start from issue number (default: 1)",
    )
    parser.add_argument(
        "--end",
        type=int,
        default=None,
        help="End at issue number (default: all)",
    )
    return parser.parse_args()


def extract_issues_from_markdown(file_path: str) -> list[dict[str, Any]]:
    """
    Extract issue JSON payloads from a markdown file.
    
    Looks for patterns like:
    **Endpoint:** `/issues/N`
    ```json
    {...}
    ```
    
    Handles the case where the JSON body contains embedded markdown code blocks.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    content = path.read_text(encoding="utf-8")
    
    issues = []
    
    # Find all endpoint markers
    endpoint_pattern = r'\*\*Endpoint:\*\*\s*`/issues/(\d+)`'
    
    for match in re.finditer(endpoint_pattern, content):
        issue_number = int(match.group(1))
        start_pos = match.end()
        
        # Find the opening ```json after the endpoint
        json_start = content.find("```json\n", start_pos)
        if json_start == -1:
            continue
        json_start += len("```json\n")
        
        # Find the JSON object boundaries by counting braces
        # This handles embedded code blocks in the body field
        brace_count = 0
        in_string = False
        escape_next = False
        json_end = json_start
        
        for i, char in enumerate(content[json_start:], start=json_start):
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                continue
            
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        json_end = i + 1
                        break
        
        if json_end > json_start:
            json_str = content[json_start:json_end]
            try:
                payload = json.loads(json_str)
                payload["_issue_number"] = issue_number
                issues.append(payload)
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse JSON for issue #{issue_number}: {e}", file=sys.stderr)
                # Debug: show first 200 chars of the extracted JSON
                print(f"  JSON preview: {json_str[:200]}...", file=sys.stderr)
    
    return issues


def perform_request(
    url: str, method: str, token: str, payload: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Execute an HTTP request to GitHub API."""
    headers = build_headers(token)
    headers["Content-Type"] = "application/json"
    data = json.dumps(payload or {}).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode()
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as error:
        detail = error.read().decode() if error.fp else error.reason
        print(f"GitHub API error {error.code}: {detail}", file=sys.stderr)
        return {"error": error.code, "message": detail}


def update_issue(token: str, issue_number: int, payload: dict[str, Any]) -> dict[str, Any]:
    """Update an existing issue via PATCH."""
    url = f"{API}/{issue_number}"
    # Remove internal tracking field
    clean_payload = {k: v for k, v in payload.items() if not k.startswith("_")}
    return perform_request(url, "PATCH", token, clean_payload)


def create_issue(token: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Create a new issue via POST."""
    clean_payload = {k: v for k, v in payload.items() if not k.startswith("_")}
    return perform_request(API, "POST", token, clean_payload)


def check_issue_exists(token: str, issue_number: int) -> bool:
    """Check if an issue exists."""
    url = f"{API}/{issue_number}"
    headers = build_headers(token)
    request = urllib.request.Request(url, method="GET", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status == 200
    except urllib.error.HTTPError:
        return False


def main() -> None:
    args = parse_args()
    
    # Collect all issues from all files
    all_issues: list[dict[str, Any]] = []
    for file_path in args.file:
        try:
            issues = extract_issues_from_markdown(file_path)
            print(f"Parsed {len(issues)} issues from {file_path}")
            all_issues.extend(issues)
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    
    if not all_issues:
        print("No issues found in the provided files.")
        sys.exit(0)
    
    # Sort by issue number
    all_issues.sort(key=lambda x: x.get("_issue_number", 999))
    
    # Filter by range
    if args.start or args.end:
        all_issues = [
            issue for issue in all_issues
            if (args.start is None or issue.get("_issue_number", 0) >= args.start)
            and (args.end is None or issue.get("_issue_number", 0) <= args.end)
        ]
    
    print(f"\nTotal issues to process: {len(all_issues)}")
    
    if args.dry_run:
        print("\n=== DRY RUN MODE ===")
        for issue in all_issues:
            num = issue.get("_issue_number", "NEW")
            title = issue.get("title", "Untitled")
            labels = issue.get("labels", [])
            body_preview = issue.get("body", "")[:100].replace("\n", " ")
            print(f"  #{num}: {title}")
            print(f"       Labels: {', '.join(labels)}")
            print(f"       Body preview: {body_preview}...")
        print("\nDry run complete. No changes made.")
        return
    
    # Execute updates
    token = require_token()
    
    results = {
        "updated": [],
        "created": [],
        "errors": [],
    }
    
    for issue in all_issues:
        issue_number = issue.get("_issue_number")
        title = issue.get("title", "Untitled")
        
        if issue_number:
            # Check if issue exists
            exists = check_issue_exists(token, issue_number)
            
            if exists:
                print(f"Updating issue #{issue_number}: {title[:50]}...")
                result = update_issue(token, issue_number, issue)
            else:
                print(f"Creating issue #{issue_number}: {title[:50]}...")
                result = create_issue(token, issue)
            
            if "error" in result:
                results["errors"].append({"number": issue_number, "error": result})
            elif exists:
                results["updated"].append(issue_number)
            else:
                results["created"].append(result.get("number", issue_number))
        else:
            print(f"Creating new issue: {title[:50]}...")
            result = create_issue(token, issue)
            if "error" in result:
                results["errors"].append({"title": title, "error": result})
            else:
                results["created"].append(result.get("number"))
    
    # Summary
    print("\n=== SUMMARY ===")
    print(f"Updated: {len(results['updated'])} issues")
    print(f"Created: {len(results['created'])} issues")
    print(f"Errors: {len(results['errors'])}")
    
    if results["errors"]:
        print("\nErrors:")
        for err in results["errors"]:
            print(f"  - {err}")
    
    output = {
        "success": len(results["errors"]) == 0,
        "updated": results["updated"],
        "created": results["created"],
        "errors": results["errors"],
    }
    print(f"\n{json.dumps(output, separators=(',', ':'))}")


if __name__ == "__main__":
    main()
