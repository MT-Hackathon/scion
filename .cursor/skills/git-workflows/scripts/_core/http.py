#!/usr/bin/env -S uv run --python 3.12
# /// script
# dependencies = ["python-dotenv>=1.0", "httpx>=0.27"]
# ///

from __future__ import annotations

import json
import sys
import time
from typing import Any, Mapping, TypedDict

import httpx


class HttpResult(TypedDict):
    ok: bool
    status_code: int
    data: Any | None
    error: str | None
    headers: dict[str, str]


def _log(verbose: bool, message: str) -> None:
    if verbose:
        sys.stderr.write(f"{message}\n")


def _parse_response(response: httpx.Response) -> Any:
    content_type = response.headers.get("Content-Type", "")
    if "application/json" in content_type:
        try:
            return response.json()
        except (json.JSONDecodeError, ValueError):
            return response.text
    return response.text or None


def _extract_error(response: httpx.Response) -> str:
    payload = _parse_response(response)
    if isinstance(payload, dict):
        if "message" in payload and isinstance(payload["message"], str):
            return payload["message"]
        if "error" in payload and isinstance(payload["error"], str):
            return payload["error"]
    if isinstance(payload, str) and payload:
        return payload
    return response.reason_phrase


def _retry_after_seconds(response: httpx.Response, fallback: float) -> float:
    header = response.headers.get("Retry-After")
    if header and header.isdigit():
        return float(header)
    return max(fallback, 0.1)


def http_request(
    method: str,
    url: str,
    *,
    headers: Mapping[str, str] | None = None,
    params: Mapping[str, Any] | None = None,
    json: Any | None = None,
    data: Any | None = None,
    timeout: float = 30.0,
    retries: int = 3,
    backoff_factor: float = 0.5,
    verbose: bool = False,
) -> HttpResult:
    attempt = 0
    delay = backoff_factor
    last_error = "Unknown error"

    while attempt <= retries:
        _log(verbose, f"[http] {method.upper()} {url} attempt={attempt + 1}")
        try:
            response = httpx.request(
                method,
                url,
                headers=dict(headers or {}),
                params=dict(params or {}),
                json=json,
                data=data,
                timeout=timeout,
            )
        except httpx.HTTPError as exc:
            last_error = str(exc)
            _log(verbose, f"[http] transport error: {last_error}")
            if attempt >= retries:
                break
            time.sleep(delay)
            delay *= 2
            attempt += 1
            continue

        status = response.status_code
        parsed = _parse_response(response)
        headers_out = dict(response.headers)

        if status == 429 or 500 <= status < 600:
            wait_seconds = _retry_after_seconds(response, delay)
            _log(verbose, f"[http] retryable status {status}, wait {wait_seconds:.2f}s")
            if attempt < retries:
                time.sleep(wait_seconds)
                delay *= 2
                attempt += 1
                continue

        if 200 <= status < 300:
            return {
                "ok": True,
                "status_code": status,
                "data": parsed,
                "error": None,
                "headers": headers_out,
            }

        error_message = _extract_error(response)
        _log(verbose, f"[http] error status {status}: {error_message}")
        return {
            "ok": False,
            "status_code": status,
            "data": parsed,
            "error": error_message,
            "headers": headers_out,
        }

    return {
        "ok": False,
        "status_code": 0,
        "data": None,
        "error": last_error,
        "headers": {},
    }


__all__ = ["HttpResult", "http_request"]
