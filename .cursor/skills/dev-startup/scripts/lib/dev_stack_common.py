"""Shared primitives for the procurement development stack scripts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
from typing import Iterable
from urllib import error, request

import psutil  # type: ignore[import-not-found]


class ServiceState(Enum):
    """State machine for reconciler startup decisions."""

    HEALTHY = "healthy"
    STOPPED_OWNED = "stopped-owned"
    UNHEALTHY_OWNED = "unhealthy-owned"
    MISSING = "missing"
    FOREIGN = "foreign"


@dataclass(frozen=True)
class ServiceDefinition:
    """Configuration for a managed service."""

    id: str
    display_name: str
    port: int
    health_url: str | None
    ownership_patterns: tuple[str, ...]
    ready_timeout_seconds: int


@dataclass(frozen=True)
class PortProcessInfo:
    """Details for the first process listening on a port."""

    pid: int
    name: str
    cmdline: str
    cwd: str


@dataclass(frozen=True)
class ContainerStatus:
    """Container state details for diagnostics."""

    name: str
    exists: bool
    running: bool
    port_mappings: str


DEFAULT_CONTAINER_NAME = os.getenv("DEV_STACK_DB_CONTAINER_NAME", "procurement-postgres")
DEFAULT_CONTAINER_IMAGE = os.getenv(
    "DEV_STACK_DB_CONTAINER_IMAGE",
    "docker.io/library/postgres:16-alpine",
)
DEFAULT_DB_USER = os.getenv("DEV_STACK_DB_USER", "procurement")
DEFAULT_DB_PASSWORD = os.getenv("DEV_STACK_DB_PASSWORD", "dev_password")
DEFAULT_DB_NAME = os.getenv("DEV_STACK_DB_NAME", "procurement_workflow")
KILL_TIMEOUT_SECONDS = int(os.getenv("DEV_STACK_KILL_TIMEOUT_SECONDS", "5"))


def derive_default_web_dir() -> Path:
    """Derive a sensible default frontend directory from script location."""

    override = os.getenv("PROCUREMENT_WEB_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parents[5]


def derive_default_api_dir() -> Path:
    """Derive a sensible default backend directory from script location."""

    override = os.getenv("PROCUREMENT_API_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return derive_default_web_dir().parent / "procurement-api"


def build_service_definitions() -> dict[str, ServiceDefinition]:
    """Build service definitions using environment-aware defaults."""

    api_port = int(os.getenv("DEV_STACK_API_PORT", "8080"))
    web_port = int(os.getenv("DEV_STACK_WEB_PORT", "4200"))
    db_port = int(os.getenv("DEV_STACK_DB_PORT", "5432"))

    api_health_url = os.getenv(
        "DEV_STACK_API_HEALTH_URL",
        f"http://localhost:{api_port}/actuator/health",
    )
    web_health_url = os.getenv("DEV_STACK_WEB_HEALTH_URL", f"http://localhost:{web_port}/")
    db_health_url = os.getenv("DEV_STACK_DB_HEALTH_URL")

    return {
        "db": ServiceDefinition(
            id="db",
            display_name="PostgreSQL",
            port=db_port,
            health_url=db_health_url,
            ownership_patterns=(r"procurement-postgres",),
            ready_timeout_seconds=int(os.getenv("DEV_STACK_DB_READY_TIMEOUT", "30")),
        ),
        "api": ServiceDefinition(
            id="api",
            display_name="API",
            port=api_port,
            health_url=api_health_url,
            ownership_patterns=(r"procurement-api", r"gradlew", r"gradle"),
            ready_timeout_seconds=int(os.getenv("DEV_STACK_API_READY_TIMEOUT", "120")),
        ),
        "web": ServiceDefinition(
            id="web",
            display_name="Frontend",
            port=web_port,
            health_url=web_health_url,
            ownership_patterns=(
                r"procurement-web",
                r"ng(\.cmd)? serve",
                r"ng\.js",
                r"npm(\.cmd)? start",
            ),
            ready_timeout_seconds=int(os.getenv("DEV_STACK_WEB_READY_TIMEOUT", "90")),
        ),
    }


def detect_container_tool() -> str | None:
    """Return preferred container CLI, favoring podman over docker."""

    if shutil.which("podman"):
        return "podman"
    if shutil.which("docker"):
        return "docker"
    return None


def resolve_executable(name: str) -> str | None:
    """Resolve executable path, handling Windows .cmd/.exe wrappers.

    On Windows, batch wrappers like npm.cmd cannot be executed by
    subprocess.Popen without shell=True. This function resolves the
    actual executable path so shell=False remains safe.
    """

    if sys.platform.startswith("win"):
        for candidate in (f"{name}.cmd", f"{name}.exe", name):
            resolved = shutil.which(candidate)
            if resolved:
                return resolved
        return None
    return shutil.which(name)


def check_port(port: int) -> bool:
    """Return True when localhost accepts TCP connections on the port."""

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _process_details(proc: psutil.Process) -> tuple[str, str]:
    """Safely return command and cwd for a process."""

    try:
        cmdline_list = proc.cmdline()
        cmdline = " ".join(cmdline_list).strip()
    except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
        cmdline = ""

    try:
        cwd = proc.cwd()
    except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
        cwd = ""

    return cmdline, cwd


def get_port_process(port: int) -> PortProcessInfo | None:
    """Return listener process details for a port when available."""

    for conn in psutil.net_connections(kind="inet"):
        if not conn.laddr or conn.status != psutil.CONN_LISTEN or conn.laddr.port != port:
            continue
        if conn.pid is None:
            continue
        try:
            proc = psutil.Process(conn.pid)
            cmdline, cwd = _process_details(proc)
            return PortProcessInfo(pid=proc.pid, name=proc.name(), cmdline=cmdline, cwd=cwd)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return None


def get_port_processes(port: int) -> list[PortProcessInfo]:
    """Return all listener processes for a port."""

    results: dict[int, PortProcessInfo] = {}
    for conn in psutil.net_connections(kind="inet"):
        if not conn.laddr or conn.status != psutil.CONN_LISTEN or conn.laddr.port != port:
            continue
        if conn.pid is None or conn.pid in results:
            continue
        try:
            proc = psutil.Process(conn.pid)
            cmdline, cwd = _process_details(proc)
            results[conn.pid] = PortProcessInfo(
                pid=proc.pid,
                name=proc.name(),
                cmdline=cmdline,
                cwd=cwd,
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return sorted(results.values(), key=lambda item: item.pid)


def check_http_health(url: str, timeout: float = 5.0) -> int:
    """Return HTTP status code, or 0 on transport failure."""

    try:
        with request.urlopen(url, timeout=timeout) as response:
            return int(response.status)
    except error.HTTPError as http_error:
        return int(http_error.code)
    except (error.URLError, TimeoutError, ValueError):
        return 0


def determine_ownership(pid: int, patterns: Iterable[str]) -> bool:
    """Return True when process cmdline/cwd matches any ownership pattern."""

    try:
        proc = psutil.Process(pid)
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return False

    cmdline, cwd = _process_details(proc)
    haystack = f"{cmdline}\n{cwd}".strip()
    if not haystack:
        return False

    return any(re.search(pattern, haystack, flags=re.IGNORECASE) for pattern in patterns)


def run_command(
    command: list[str],
    cwd: Path | None = None,
    timeout: float | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a command and capture output for diagnostics."""

    try:
        return subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except FileNotFoundError:
        return subprocess.CompletedProcess(
            args=command, returncode=127, stdout="", stderr=f"Command not found: {command[0]}"
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            args=command, returncode=124, stdout="", stderr=f"Command timed out after {timeout}s"
        )


def inspect_container(container_tool: str | None, name: str) -> ContainerStatus:
    """Inspect container existence, running state, and port mappings."""

    if not container_tool:
        return ContainerStatus(name=name, exists=False, running=False, port_mappings="-")

    exists_result = run_command([container_tool, "inspect", name])
    if exists_result.returncode != 0:
        return ContainerStatus(name=name, exists=False, running=False, port_mappings="-")

    running_result = run_command(
        [container_tool, "inspect", "--format", "{{.State.Running}}", name]
    )
    running = running_result.returncode == 0 and running_result.stdout.strip().lower() == "true"

    ports_result = run_command([container_tool, "port", name])
    port_mappings = ports_result.stdout.strip() if ports_result.returncode == 0 else "-"
    if not port_mappings:
        port_mappings = "-"

    return ContainerStatus(name=name, exists=True, running=running, port_mappings=port_mappings)
