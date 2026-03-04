#!/usr/bin/env -S uv run --python 3.12
# /// script
# dependencies = ["python-dotenv>=1.0", "httpx>=0.27"]
# ///

from __future__ import annotations

import argparse
import os
import sys
from typing import Iterable

from .providers import PROJECT_ENV_BY_PROVIDER, TOKEN_ENV_BY_PROVIDER, ProviderName, load_env


def _first_defined(keys: Iterable[str]) -> str | None:
    for key in keys:
        value = os.environ.get(key)
        if value:
            return value
    return None


def add_provider_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--provider",
        choices=["gitlab", "github", "state"],
        default="gitlab",
        help="Target provider: gitlab, github, or state (state gitlab).",
    )
    parser.add_argument(
        "--project",
        help="Project path or ID. Falls back to provider-specific env vars.",
    )
    parser.add_argument(
        "--token",
        help="Token override. Otherwise resolved from provider-specific env vars.",
    )


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview actions without performing mutations.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose request logging.",
    )


def validate_provider_args(args: argparse.Namespace) -> None:
    load_env()
    provider: ProviderName = getattr(args, "provider", "gitlab") or "gitlab"  # type: ignore[assignment]

    if provider not in TOKEN_ENV_BY_PROVIDER:
        raise SystemExit("Provider must be one of: gitlab, github, state.")

    token = getattr(args, "token", None) or _first_defined(TOKEN_ENV_BY_PROVIDER[provider])
    if not token:
        env_list = ", ".join(TOKEN_ENV_BY_PROVIDER[provider])
        raise SystemExit(f"Missing token for {provider}. Set one of: {env_list}, or pass --token.")

    project = getattr(args, "project", None) or _first_defined(PROJECT_ENV_BY_PROVIDER.get(provider, []))
    if not project:
        env_list = ", ".join(PROJECT_ENV_BY_PROVIDER.get(provider, []))
        raise SystemExit(
            f"Missing project for {provider}. Provide --project or set one of: {env_list}."
        )


__all__ = ["add_common_args", "add_provider_args", "validate_provider_args"]
