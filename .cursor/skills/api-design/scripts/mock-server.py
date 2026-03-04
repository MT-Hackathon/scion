#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Run and manage a Prism mock server for OpenAPI development."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Sequence
from urllib import error as urllib_error
from urllib import request as urllib_request

EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_USAGE = 2


def run_command(
    args: Sequence[str],
    cwd: Path,
    timeout: int,
) -> subprocess.CompletedProcess[str]:
    """Run a subprocess command with explicit timeout and cwd."""
    return subprocess.run(
        list(args),
        cwd=str(cwd),
        timeout=timeout,
        capture_output=True,
        text=True,
        check=False,
    )


def can_connect(host: str, port: int, timeout: float = 1.0) -> bool:
    """Return True when a TCP connection can be established."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        return sock.connect_ex((host, port)) == 0


def health_check(host: str, port: int, endpoint: str, timeout: float) -> tuple[bool, str]:
    """Probe HTTP health endpoint for the mock server."""
    url = f"http://{host}:{port}{endpoint}"
    req = urllib_request.Request(url, method="GET")
    try:
        with urllib_request.urlopen(req, timeout=timeout) as response:
            return (200 <= response.status < 500, f"HTTP {response.status} {url}")
    except urllib_error.URLError as exc:
        return (False, f"unreachable {url}: {exc}")


def process_exists(pid: int) -> bool:
    """Best-effort check whether a process still exists."""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def stop_pid(pid: int, grace_seconds: float) -> bool:
    """Terminate process by PID with graceful timeout and forced fallback."""
    if not process_exists(pid):
        return True

    os.kill(pid, signal.SIGTERM)
    deadline = time.monotonic() + grace_seconds
    while time.monotonic() < deadline:
        if not process_exists(pid):
            return True
        time.sleep(0.2)

    if hasattr(signal, "SIGKILL"):
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            return True
    else:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            return True
    time.sleep(0.2)
    return not process_exists(pid)


def read_state(state_file: Path) -> dict[str, object] | None:
    """Read pid/state JSON file."""
    if not state_file.exists():
        return None
    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def write_state(state_file: Path, state: dict[str, object]) -> None:
    """Persist pid/state JSON file."""
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")


def remove_state(state_file: Path) -> None:
    """Delete state file if present."""
    if state_file.exists():
        state_file.unlink()


def resolve_prism_command(prism_command: str, cwd: Path) -> list[str]:
    """Resolve prism executable command vector."""
    if prism_command.strip():
        return shlex.split(prism_command)

    prism = run_command(["prism", "--version"], cwd=cwd, timeout=10)
    if prism.returncode == 0:
        return ["prism"]

    npx = run_command(["npx", "--version"], cwd=cwd, timeout=10)
    if npx.returncode == 0:
        return ["npx", "-y", "@stoplight/prism-cli"]

    raise RuntimeError("Prism CLI not found. Install prism or ensure npx is available.")


def start_server(args: argparse.Namespace, cwd: Path) -> int:
    """Start mock server and keep process attached until interrupted."""
    spec = Path(args.spec).expanduser().resolve()
    if not spec.exists() or not spec.is_file():
        print(f"[error] spec file not found: {spec}")
        return EXIT_USAGE

    if args.port <= 0 or args.port > 65535:
        print(f"[error] invalid port: {args.port}")
        return EXIT_USAGE

    if can_connect(args.host, args.port):
        print(f"[error] {args.host}:{args.port} is already in use.")
        return EXIT_ERROR

    try:
        prism_base = resolve_prism_command(args.prism_command, cwd)
    except RuntimeError as exc:
        print(f"[error] {exc}")
        return EXIT_ERROR

    command = [
        *prism_base,
        "mock",
        str(spec),
        "--host",
        args.host,
        "--port",
        str(args.port),
    ]
    if args.dynamic:
        command.append("--dynamic")

    log_path = Path(args.log_file).expanduser().resolve()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    state_path = Path(args.state_file).expanduser().resolve()

    with log_path.open("a", encoding="utf-8") as log_handle:
        process = subprocess.Popen(
            command,
            cwd=str(cwd),
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            text=True,
        )

    write_state(
        state_path,
        {
            "pid": process.pid,
            "spec": str(spec),
            "host": args.host,
            "port": args.port,
            "log_file": str(log_path),
        },
    )
    print(f"[ok] started prism pid={process.pid} on http://{args.host}:{args.port}")
    print(f"[ok] logs: {log_path}")

    deadline = time.monotonic() + args.health_wait_seconds
    healthy = False
    last_message = ""
    while time.monotonic() < deadline:
        healthy, last_message = health_check(
            args.host,
            args.port,
            args.health_endpoint,
            timeout=args.health_timeout_seconds,
        )
        if healthy:
            break
        if process.poll() is not None:
            print("[error] prism exited before becoming healthy.")
            remove_state(state_path)
            return EXIT_ERROR
        time.sleep(args.health_poll_seconds)

    if healthy:
        print(f"[ok] health check passed: {last_message}")
    else:
        print(f"[warn] health check did not confirm readiness: {last_message}")

    try:
        while True:
            try:
                process.wait(timeout=1)
                break
            except subprocess.TimeoutExpired:
                continue
    except KeyboardInterrupt:
        print("\n[info] received Ctrl+C, stopping prism...")
        if stop_pid(process.pid, grace_seconds=args.stop_timeout_seconds):
            print("[ok] prism stopped gracefully.")
            return EXIT_SUCCESS
        else:
            print("[error] unable to stop prism cleanly.")
            remove_state(state_path)
            return EXIT_ERROR
    finally:
        remove_state(state_path)

    return EXIT_SUCCESS if process.returncode == 0 else EXIT_ERROR


def stop_server(args: argparse.Namespace) -> int:
    """Stop mock server using state-file PID."""
    state_path = Path(args.state_file).expanduser().resolve()
    state = read_state(state_path)
    if not state:
        print("[error] no state file found; server may not be running.")
        return EXIT_ERROR

    pid = state.get("pid")
    if not isinstance(pid, int):
        print("[error] invalid pid in state file.")
        remove_state(state_path)
        return EXIT_ERROR

    if stop_pid(pid, grace_seconds=args.stop_timeout_seconds):
        print(f"[ok] stopped prism pid={pid}")
        remove_state(state_path)
        return EXIT_SUCCESS

    print(f"[error] failed to stop prism pid={pid}")
    return EXIT_ERROR


def health_server(args: argparse.Namespace) -> int:
    """Run independent health check request."""
    ok, message = health_check(
        args.host,
        args.port,
        args.health_endpoint,
        timeout=args.health_timeout_seconds,
    )
    if ok:
        print(f"[ok] {message}")
        return EXIT_SUCCESS
    print(f"[error] {message}")
    return EXIT_ERROR


def build_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        prog="mock-server.py",
        description="Start and manage a Prism mock server.",
    )
    parser.add_argument(
        "--state-file",
        default=os.environ.get("MOCK_SERVER_STATE_FILE", ".mock-server-state.json"),
        help="Path for PID/state file (default from MOCK_SERVER_STATE_FILE).",
    )
    parser.add_argument(
        "--log-file",
        default=os.environ.get("MOCK_SERVER_LOG_FILE", "mock-server.log"),
        help="Path for mock server logs (default from MOCK_SERVER_LOG_FILE).",
    )
    parser.add_argument(
        "--prism-command",
        default=os.environ.get("PRISM_COMMAND", ""),
        help="Optional prism command override (for example: 'prism' or 'npx -y @stoplight/prism-cli').",
    )
    parser.add_argument(
        "--health-endpoint",
        default=os.environ.get("MOCK_SERVER_HEALTH_ENDPOINT", "/"),
        help="Health check endpoint path (default from MOCK_SERVER_HEALTH_ENDPOINT).",
    )
    parser.add_argument(
        "--health-timeout-seconds",
        type=float,
        default=float(os.environ.get("MOCK_SERVER_HEALTH_TIMEOUT_SECONDS", "2")),
        help="Single health request timeout seconds.",
    )
    parser.add_argument(
        "--stop-timeout-seconds",
        type=float,
        default=float(os.environ.get("MOCK_SERVER_STOP_TIMEOUT_SECONDS", "8")),
        help="Grace period before forced kill on stop.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser("start", help="Start Prism server.")
    start.add_argument("--spec", required=True, help="Path to OpenAPI spec file.")
    start.add_argument("--port", type=int, default=4010, help="Port (default: 4010).")
    start.add_argument("--host", default="127.0.0.1", help="Host (default: 127.0.0.1).")
    start.add_argument(
        "--dynamic",
        action="store_true",
        help="Enable Prism dynamic response mode.",
    )
    start.add_argument(
        "--health-wait-seconds",
        type=float,
        default=float(os.environ.get("MOCK_SERVER_HEALTH_WAIT_SECONDS", "20")),
        help="Max time to wait for first healthy response.",
    )
    start.add_argument(
        "--health-poll-seconds",
        type=float,
        default=float(os.environ.get("MOCK_SERVER_HEALTH_POLL_SECONDS", "1")),
        help="Polling interval while waiting for readiness.",
    )

    subparsers.add_parser("stop", help="Stop Prism server using state file.")

    health = subparsers.add_parser("health", help="Check Prism health endpoint.")
    health.add_argument("--port", type=int, default=4010, help="Port (default: 4010).")
    health.add_argument("--host", default="127.0.0.1", help="Host (default: 127.0.0.1).")

    return parser


def main() -> int:
    """Program entrypoint."""
    parser = build_parser()
    try:
        args = parser.parse_args()
    except SystemExit as exc:
        code = int(exc.code) if isinstance(exc.code, int) else EXIT_USAGE
        return EXIT_USAGE if code != 0 else EXIT_SUCCESS

    cwd = Path.cwd().resolve()
    if args.command == "start":
        return start_server(args, cwd)
    if args.command == "stop":
        return stop_server(args)
    if args.command == "health":
        return health_server(args)

    return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
