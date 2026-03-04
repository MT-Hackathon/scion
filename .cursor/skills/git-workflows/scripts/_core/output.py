#!/usr/bin/env -S uv run --python 3.12
# /// script
# dependencies = ["python-dotenv>=1.0", "httpx>=0.27"]
# ///

from __future__ import annotations

import sys
from typing import Iterable, NoReturn

stdout_reconfigure = getattr(sys.stdout, "reconfigure", None)
if callable(stdout_reconfigure):
    stdout_reconfigure(encoding="utf-8")

stderr_reconfigure = getattr(sys.stderr, "reconfigure", None)
if callable(stderr_reconfigure):
    stderr_reconfigure(encoding="utf-8")


def emit_text(lines: Iterable[str]) -> None:
    for line in lines:
        sys.stdout.write(f"{line}\n")


def emit_markdown(content: str) -> None:
    sys.stdout.write(f"{content}\n")


def emit_error(msg: str, exit_code: int = 1) -> NoReturn:
    sys.stderr.write(f"{msg}\n")
    raise SystemExit(exit_code)


def truncate(text: str, max_len: int = 200) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


__all__ = ["emit_error", "emit_markdown", "emit_text", "truncate"]
