#!/usr/bin/env -S uv run --python 3.12
# /// script
# dependencies = ["python-dotenv>=1.0", "httpx>=0.27"]
# ///

from __future__ import annotations

import os
import sys
import urllib.parse
from dataclasses import dataclass
from typing import Any, Iterable, Literal, Protocol

from .http import HttpResult, http_request

ProviderName = Literal["gitlab", "github", "state"]


class Provider(Protocol):
    def request(self, method: str, endpoint: str, **kwargs: Any) -> HttpResult: ...


BASE_URLS: dict[ProviderName, str] = {
    "gitlab": "https://gitlab.com/api/v4",
    "github": "https://api.github.com",
    "state": "https://git.mt.gov/api/v4",
}

TOKEN_ENV_BY_PROVIDER: dict[ProviderName, list[str]] = {
    "gitlab": ["GITLAB_TOKEN", "CDO_GITLAB_TOKEN", "GITLAB_PERSONAL_ACCESS_TOKEN"],
    "github": ["GITHUB_TOKEN", "GITHUB_PERSONAL_ACCESS_TOKEN"],
    "state": ["STATE_GITLAB_TOKEN", "STATE_GITLAB_PERSONAL_ACCESS_TOKEN"],
}

PROJECT_ENV_BY_PROVIDER: dict[ProviderName, list[str]] = {
    "gitlab": [
        "GITLAB_PROJECT",
        "GITLAB_PROJECT_ID",
        "GITLAB_PROJECT_PATH",
        "CDO_GITLAB_PROJECT_ID",
        "CDO_GITLAB_PROJECT_PATH",
    ],
    "github": ["GITHUB_REPOSITORY", "GITHUB_REPO"],
    "state": [
        "STATE_GITLAB_PROJECT",
        "STATE_GITLAB_PROJECT_ID",
        "STATE_GITLAB_PROJECT_PATH",
    ],
}


def load_env() -> None:
    """Load .env using python-dotenv if available."""
    try:
        from dotenv import find_dotenv, load_dotenv

        env_path = find_dotenv(usecwd=True) or find_dotenv(usecwd=False)
        if env_path:
            load_dotenv(env_path)
    except ImportError:
        return


def _first_defined(keys: Iterable[str]) -> str | None:
    for key in keys:
        value = os.environ.get(key)
        if value:
            return value
    return None


def _normalize_name(name: str) -> ProviderName:
    cleaned = name.strip().lower()
    if cleaned in ("state-gitlab", "state_gitlab", "stategitlab"):
        return "state"
    if cleaned not in BASE_URLS:
        raise SystemExit(f"Unsupported provider '{name}'. Use gitlab, github, or state.")
    return cleaned  # type: ignore[return-value]


def _resolve_token(provider: ProviderName, token_override: str | None) -> str:
    if token_override:
        return token_override

    token = _first_defined(TOKEN_ENV_BY_PROVIDER[provider])
    if token:
        return token

    env_list = ", ".join(TOKEN_ENV_BY_PROVIDER[provider])
    raise SystemExit(f"Missing token for {provider}. Set one of: {env_list}")


def _resolve_project(provider: ProviderName, project_override: str | None) -> str | None:
    if project_override:
        return project_override
    return _first_defined(PROJECT_ENV_BY_PROVIDER.get(provider, []))


def _auth_headers(provider: ProviderName, token: str) -> dict[str, str]:
    if provider == "github":
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "git-workflows-scripts",
        }
    return {
        "PRIVATE-TOKEN": token,
        "User-Agent": "git-workflows-scripts",
    }


@dataclass
class RestProvider:
    name: ProviderName
    base_url: str
    token: str
    project: str | None = None
    verbose: bool = False

    def request(self, method: str, endpoint: str, **kwargs: Any) -> HttpResult:
        headers = kwargs.pop("headers", None)
        url = self._build_url(endpoint)
        merged_headers = {**_auth_headers(self.name, self.token), **(headers or {})}
        return http_request(
            method=method,
            url=url,
            headers=merged_headers,
            verbose=self.verbose,
            **kwargs,
        )

    def _build_url(self, endpoint: str) -> str:
        if endpoint.startswith(("http://", "https://")):
            return endpoint

        resolved = endpoint
        if "{project}" in endpoint and self.project:
            resolved = endpoint.replace("{project}", urllib.parse.quote(self.project, safe=""))

        return f"{self.base_url.rstrip('/')}/{resolved.lstrip('/')}"


def get_provider(
    name: str,
    project: str | None = None,
    *,
    token: str | None = None,
    verbose: bool = False,
) -> Provider:
    """
    Get configured provider.

    name: 'gitlab' | 'github' | 'state' (state-gitlab)
    project: project path/id, or read from env

    Token resolution:
    - gitlab: GITLAB_TOKEN or CDO_GITLAB_TOKEN
    - github: GITHUB_TOKEN
    - state: STATE_GITLAB_TOKEN
    """
    load_env()
    provider_name = _normalize_name(name)
    resolved_token = _resolve_token(provider_name, token)
    resolved_project = _resolve_project(provider_name, project)

    return RestProvider(
        name=provider_name,
        base_url=BASE_URLS[provider_name],
        token=resolved_token,
        project=resolved_project,
        verbose=verbose,
    )


__all__ = [
    "BASE_URLS",
    "PROJECT_ENV_BY_PROVIDER",
    "Provider",
    "ProviderName",
    "RestProvider",
    "TOKEN_ENV_BY_PROVIDER",
    "get_provider",
    "load_env",
]
