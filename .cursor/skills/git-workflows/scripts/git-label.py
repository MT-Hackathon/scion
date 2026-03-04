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
from collections.abc import Callable
from typing import Any, Sequence

from _core import (
    add_common_args,
    add_provider_args,
    emit_error,
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


def normalize_color(provider_name: str, color: str | None) -> str | None:
    if not color:
        return None
    color = color.strip()
    if not color:
        return None
    if provider_name in ("gitlab", "state"):
        return color if color.startswith("#") else f"#{color}"
    return color.lstrip("#")


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------


def op_create(provider: Any, provider_name: str, args: argparse.Namespace) -> None:
    project = ensure_project(provider)
    color = normalize_color(provider_name, args.color)
    if args.dry_run:
        emit_text(
            [
                f"[dry-run] create label '{args.name}'",
                f"color={color or '(none)'}",
                f"description={truncate(args.description or '', 120)}",
            ]
        )
        return

    if provider_name in ("gitlab", "state"):
        payload = {"name": args.name}
        if color:
            payload["color"] = color
        if args.description:
            payload["description"] = args.description
        result = provider.request("POST", "/projects/{project}/labels", json=payload)
        ensure_ok_dict(result, "Create label")
    else:
        payload = {"name": args.name}
        if color:
            payload["color"] = color.lstrip("#")
        if args.description:
            payload["description"] = args.description
        result = provider.request("POST", f"/repos/{project}/labels", json=payload)
        ensure_ok_dict(result, "Create label")

    emit_text([f"Created label '{args.name}'"])


def op_update(provider: Any, provider_name: str, args: argparse.Namespace) -> None:
    project = ensure_project(provider)
    color = normalize_color(provider_name, args.color)
    if provider_name in ("gitlab", "state"):
        payload: dict[str, Any] = {"name": args.name}
        if args.description:
            payload["description"] = args.description
        if color:
            payload["color"] = color
        if args.new_name:
            payload["new_name"] = args.new_name

        if args.dry_run:
            emit_text([f"[dry-run] update label '{args.name}' -> {payload}"])
            return

        result = provider.request("PUT", "/projects/{project}/labels", json=payload)
        ensure_ok_dict(result, "Update label")
    else:
        payload = {}
        if args.new_name:
            payload["new_name"] = args.new_name
        if color:
            payload["color"] = color.lstrip("#")
        if args.description is not None:
            payload["description"] = args.description

        if args.dry_run:
            emit_text([f"[dry-run] update label '{args.name}' -> {payload}"])
            return

        endpoint = f"/repos/{project}/labels/{args.name}"
        result = provider.request("PATCH", endpoint, json=payload)
        ensure_ok_dict(result, "Update label")

    emit_text([f"Updated label '{args.new_name or args.name}'"])


def op_delete(provider: Any, provider_name: str, args: argparse.Namespace) -> None:
    project = ensure_project(provider)
    if args.dry_run:
        emit_text([f"[dry-run] delete label '{args.name}'"])
        return

    if provider_name in ("gitlab", "state"):
        result = provider.request(
            "DELETE",
            "/projects/{project}/labels",
            params={"name": args.name},
        )
    else:
        endpoint = f"/repos/{project}/labels/{args.name}"
        result = provider.request("DELETE", endpoint)

    if not result.get("ok"):
        status = result.get("status_code")
        detail = result.get("error") or "Unknown error"
        emit_error(f"Delete failed (HTTP {status}): {detail}")
    emit_text([f"Deleted label '{args.name}'"])


def op_list(provider: Any, provider_name: str) -> None:
    project = ensure_project(provider)
    if provider_name in ("gitlab", "state"):
        result = provider.request("GET", "/projects/{project}/labels", params={"per_page": "100"})
    else:
        result = provider.request("GET", f"/repos/{project}/labels", params={"per_page": "100"})
    items = ensure_ok_list(result, "List labels")
    lines = []
    for item in items:
        name = item.get("name") or ""
        color = item.get("color") or ""
        desc = item.get("description") or ""
        lines.append(f"- {name} ({color}) {truncate(desc, 100)}")
    emit_text(lines or ["(no labels)"])


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage repository labels across providers.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def with_shared(p: argparse.ArgumentParser) -> argparse.ArgumentParser:
        add_provider_args(p)
        add_common_args(p)
        return p

    p_create = with_shared(subparsers.add_parser("create", help="Create a label."))
    p_create.add_argument("--name", required=True, help="Label name.")
    p_create.add_argument("--color", required=True, help="Label color (e.g., #ff0000).")
    p_create.add_argument("--description", help="Label description.")

    p_update = with_shared(subparsers.add_parser("update", help="Update a label."))
    p_update.add_argument("name", help="Existing label name.")
    p_update.add_argument("--new-name", help="New label name.")
    p_update.add_argument("--color", help="New color.")
    p_update.add_argument("--description", help="New description.")

    p_delete = with_shared(subparsers.add_parser("delete", help="Delete a label."))
    p_delete.add_argument("name", help="Label name to delete.")

    p_list = with_shared(subparsers.add_parser("list", help="List labels."))

    return parser


def _cmd_create(provider: Any, provider_name: str, args: argparse.Namespace) -> None:
    op_create(provider, provider_name, args)


def _cmd_update(provider: Any, provider_name: str, args: argparse.Namespace) -> None:
    op_update(provider, provider_name, args)


def _cmd_delete(provider: Any, provider_name: str, args: argparse.Namespace) -> None:
    op_delete(provider, provider_name, args)


def _cmd_list(provider: Any, provider_name: str, args: argparse.Namespace) -> None:
    del args
    op_list(provider, provider_name)


_COMMANDS: dict[str, Callable[[Any, str, argparse.Namespace], None]] = {
    "create": _cmd_create,
    "update": _cmd_update,
    "delete": _cmd_delete,
    "list": _cmd_list,
}


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    validate_provider_args(args)
    provider = get_provider(
        args.provider,
        project=args.project,
        token=getattr(args, "token", None),
        verbose=args.verbose,
    )

    handler = _COMMANDS.get(args.command)
    if handler is None:
        parser.error(f"Unknown command: {args.command}")
    handler(provider, args.provider, args)


if __name__ == "__main__":
    main()
