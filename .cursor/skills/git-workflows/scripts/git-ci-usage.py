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
import datetime as dt
from typing import Any, Sequence

from _core import (
    add_common_args,
    add_provider_args,
    emit_error,
    emit_text,
    get_provider,
    validate_provider_args,
)

GRAPHQL_URL = "https://gitlab.com/api/graphql"
MAX_BAR_WIDTH = 20


def ensure_gitlab_provider(name: str) -> None:
    if name != "gitlab":
        emit_error("git-ci-usage supports the gitlab provider only.")


def ensure_project(provider: Any) -> str:
    project = getattr(provider, "project", None)
    if not isinstance(project, str) or not project:
        emit_error("Project must be provided via --project or environment.")
        raise AssertionError("unreachable")
    return project


def ensure_ok_dict(result: Any, context: str) -> dict[str, Any]:
    if result.get("ok") and isinstance(result.get("data"), dict):
        return result["data"]
    status = result.get("status_code")
    detail = result.get("error") or "Unknown error"
    emit_error(f"{context} failed (HTTP {status}): {detail}")
    raise AssertionError("unreachable")


def to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def month_title(month_iso: str | None) -> str:
    if not month_iso:
        return "Unknown Month"
    try:
        parsed = dt.date.fromisoformat(month_iso)
    except ValueError:
        return month_iso
    return parsed.strftime("%B %Y")


def resolve_project_path(provider: Any, project: str) -> str:
    if "/" in project:
        return project
    result = provider.request("GET", "/projects/{project}")
    data = ensure_ok_dict(result, "Resolve project path")
    path = data.get("path_with_namespace")
    if not isinstance(path, str) or "/" not in path:
        emit_error("Could not resolve project path_with_namespace from project id.")
        raise AssertionError("unreachable")
    return path


def resolve_group(provider: Any, project: str) -> tuple[int, str]:
    project_path = resolve_project_path(provider, project)
    group_path = project_path.split("/", 1)[0]
    result = provider.request("GET", f"/namespaces/{group_path}")
    data = ensure_ok_dict(result, "Resolve namespace")
    group_id = to_int(data.get("id"))
    if group_id <= 0:
        emit_error(f"Namespace '{group_path}' did not return a valid id.")
    return group_id, group_path


def fetch_group_info(provider: Any, group_id: int) -> dict[str, Any]:
    result = provider.request("GET", f"/groups/{group_id}")
    return ensure_ok_dict(result, "Fetch group info")


def fetch_namespace_details(provider: Any, group_id: int) -> dict[str, Any]:
    result = provider.request("GET", f"/namespaces/{group_id}")
    return ensure_ok_dict(result, "Fetch namespace details")


def fetch_ci_usage(provider: Any, group_id: int, months: int) -> list[dict[str, Any]]:
    headers = {"PRIVATE-TOKEN": provider.token}
    gid = f"gid://gitlab/Group/{group_id}"
    query = f"""
{{
  ciMinutesUsage(namespaceId: "{gid}", first: {months}) {{
    nodes {{
      month
      monthIso8601
      minutes
      projects {{
        nodes {{
          minutes
          project {{
            id
            name
          }}
        }}
      }}
    }}
  }}
}}
"""
    payload = {"query": query}
    result = provider.request("POST", GRAPHQL_URL, headers=headers, json=payload)
    data = ensure_ok_dict(result, "Fetch CI usage")
    errors = data.get("errors")
    if isinstance(errors, list) and errors:
        first = errors[0]
        message = first.get("message") if isinstance(first, dict) else str(first)
        emit_error(f"Fetch CI usage failed: {message}")
    usage = data.get("data", {}).get("ciMinutesUsage", {}).get("nodes", [])
    if not isinstance(usage, list):
        emit_error("Unexpected GraphQL response shape for ciMinutesUsage.")
    return [item for item in usage if isinstance(item, dict)]


def sort_nodes_desc(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(nodes, key=lambda n: str(n.get("monthIso8601") or n.get("month") or ""), reverse=True)


def month_bucket(month_value: Any) -> str:
    text = str(month_value or "unknown")
    if len(text) >= 7 and text[4] == "-":
        return text[:7]
    return text


def fmt_quota_line(limit: int, plan: str | None) -> str:
    if limit > 0:
        limit_text = f"{limit:,}"
    else:
        limit_text = "unlimited"
    plan_text = plan or "unknown"
    return f"Quota: {limit_text} min/month ({plan_text})"


def render_summary(
    usage_nodes: list[dict[str, Any]],
    quota_limit: int,
    plan: str | None,
    end_date: str | None,
) -> None:
    if not usage_nodes:
        emit_text(["No CI usage data returned for this namespace."])
        return

    current = sort_nodes_desc(usage_nodes)[0]
    minutes_used = to_int(current.get("minutes"))
    month_label = month_title(current.get("monthIso8601"))

    if quota_limit > 0:
        pct = (minutes_used / quota_limit) * 100
        usage_line = f"Usage: {minutes_used:,} / {quota_limit:,} ({pct:.1f}%)"
    else:
        usage_line = f"Usage: {minutes_used:,} / unlimited"

    plan_line = f"Plan: {plan or 'unknown'}"
    if end_date:
        plan_line += f" (expires {end_date})"

    project_rows = current.get("projects", {}).get("nodes", [])
    if not isinstance(project_rows, list):
        project_rows = []

    per_project: list[tuple[str, int]] = []
    for row in project_rows:
        if not isinstance(row, dict):
            continue
        name = row.get("project", {}).get("name")
        if not isinstance(name, str) or not name:
            name = "(unknown)"
        per_project.append((name, to_int(row.get("minutes"))))

    per_project.sort(key=lambda item: item[1], reverse=True)
    total = sum(minutes for _, minutes in per_project)
    name_width = max([len(name) for name, _ in per_project] + [5, len("Total")])

    lines = [
        f"## CI/CD Compute Minutes - {month_label}",
        "",
        usage_line,
        plan_line,
        "",
        "### Per-Project Breakdown",
    ]
    if not per_project:
        lines.append("  (no per-project data)")
    else:
        for name, minutes in per_project:
            lines.append(f"  {name:<{name_width}}  {minutes:>5} min")
        lines.append(f"  {'-' * name_width}  {'-' * 5} ---")
        lines.append(f"  {'Total':<{name_width}}  {total:>5} min")

    emit_text(lines)


def bar(minutes: int, max_minutes: int) -> str:
    if max_minutes <= 0 or minutes <= 0:
        return ""
    width = max(1, round((minutes / max_minutes) * MAX_BAR_WIDTH))
    return "#" * width


def render_history(usage_nodes: list[dict[str, Any]], months_requested: int, quota_limit: int, plan: str | None) -> None:
    if not usage_nodes:
        emit_text(["No CI usage history returned for this namespace."])
        return

    rows: list[tuple[str, int]] = []
    for node in sort_nodes_desc(usage_nodes):
        rows.append((month_bucket(node.get("monthIso8601") or node.get("month")), to_int(node.get("minutes"))))

    max_minutes = max((minutes for _, minutes in rows), default=0)
    lines = [
        f"## CI/CD Compute Minutes - {months_requested} Month History",
        "",
    ]
    for month_key, minutes in rows:
        lines.append(f"  {month_key:<9} {minutes:>5} min {bar(minutes, max_minutes)}")
    lines.append("")
    lines.append(fmt_quota_line(quota_limit, plan))
    emit_text(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Query GitLab CI/CD compute minutes usage.")
    add_provider_args(parser)
    add_common_args(parser)

    subs = parser.add_subparsers(dest="command", required=True)
    subs.add_parser("summary", help="Show current month CI usage and per-project breakdown.")
    p_history = subs.add_parser("history", help="Show monthly CI usage trend.")
    p_history.add_argument(
        "--months",
        type=int,
        default=6,
        help="Number of months to return (default: 6).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    validate_provider_args(args)
    ensure_gitlab_provider(args.provider)

    if args.command == "history" and args.months <= 0:
        emit_error("--months must be >= 1.")

    provider = get_provider(
        args.provider,
        project=args.project,
        token=getattr(args, "token", None),
        verbose=args.verbose,
    )
    project = ensure_project(provider)
    group_id, _group_path = resolve_group(provider, project)
    group_info = fetch_group_info(provider, group_id)
    namespace = fetch_namespace_details(provider, group_id)

    quota_limit = to_int(group_info.get("shared_runners_minutes_limit"))
    plan = namespace.get("plan")
    plan_name = plan if isinstance(plan, str) else "unknown"
    end_date = namespace.get("end_date")
    end_date_text = end_date if isinstance(end_date, str) else None

    if args.command == "summary":
        usage_nodes = fetch_ci_usage(provider, group_id, 1)
        render_summary(usage_nodes, quota_limit, plan_name, end_date_text)
    elif args.command == "history":
        usage_nodes = fetch_ci_usage(provider, group_id, args.months)
        render_history(usage_nodes, args.months, quota_limit, plan_name)
    else:
        emit_error(f"Unknown command {args.command}")


if __name__ == "__main__":
    main()
