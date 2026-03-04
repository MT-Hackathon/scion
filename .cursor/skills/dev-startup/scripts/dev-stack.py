#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = ["psutil"]
# ///
"""Unified development stack controller for procurement-web/procurement-api."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

import psutil  # type: ignore[import-not-found]

from lib.dev_stack_common import (
    ContainerStatus,
    DEFAULT_CONTAINER_IMAGE,
    DEFAULT_CONTAINER_NAME,
    DEFAULT_DB_NAME,
    DEFAULT_DB_PASSWORD,
    DEFAULT_DB_USER,
    KILL_TIMEOUT_SECONDS,
    ServiceState,
    build_service_definitions,
    check_http_health,
    check_port,
    derive_default_api_dir,
    derive_default_web_dir,
    detect_container_tool,
    determine_ownership,
    get_port_process,
    get_port_processes,
    inspect_container,
    resolve_executable,
    run_command,
)


@dataclass(frozen=True)
class ClassifiedState:
    """State and detail produced by service classification."""

    state: ServiceState
    detail: str


class Logger:
    """Minimal prefix logger with failure tracking."""

    def __init__(self, prefix: str) -> None:
        self.prefix = prefix
        self.had_failures = False

    def _print(self, label: str, message: str) -> None:
        print(f"{self.prefix} [{label}] {message}")

    def info(self, message: str) -> None:
        self._print("INFO", message)

    def ok(self, message: str) -> None:
        self._print("OK", message)

    def skip(self, message: str) -> None:
        self._print("SKIP", message)

    def fail(self, message: str) -> None:
        self.had_failures = True
        self._print("FAIL", message)


def wait_seconds(seconds: int) -> None:
    """Wait helper to keep sleeps explicit and testable."""

    time.sleep(seconds)


def terminate_pid(pid: int, label: str, logger: Logger, force: bool = False) -> None:
    """Terminate then kill process if it survives timeout."""

    try:
        process = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return

    if force:
        process.kill()
        return

    process.terminate()
    try:
        process.wait(timeout=KILL_TIMEOUT_SECONDS)
        return
    except psutil.TimeoutExpired:
        process.kill()
        logger.info(f"{label} (PID {pid}) required hard kill")
    except psutil.NoSuchProcess:
        return


def report_foreign(service_name: str, port: int, logger: Logger) -> None:
    """Print rich diagnostics for foreign ownership conflicts."""

    process_info = get_port_process(port)
    logger.fail(f"{service_name} blocked: port {port} held by foreign process")
    if process_info is None:
        logger.info("  PID: unknown")
        logger.info("  Command: unavailable")
        logger.info("  CWD: unavailable")
        return
    logger.info(f"  PID: {process_info.pid}")
    logger.info(f"  Command: {process_info.cmdline or '<unavailable>'}")
    logger.info(f"  CWD: {process_info.cwd or '<unavailable>'}")
    logger.info("  Resolve manually, then retry")


def classify_database(container_tool: str | None, services: dict[str, Any]) -> ClassifiedState:
    """Classify database according to reconciler state machine."""

    db = services["db"]
    db_status = inspect_container(container_tool, DEFAULT_CONTAINER_NAME)
    listener = get_port_process(db.port)

    if listener is not None:
        if db_status.running:
            if container_tool is None:
                return ClassifiedState(ServiceState.FOREIGN, "container runtime missing")
            health = run_command(
                [container_tool, "exec", DEFAULT_CONTAINER_NAME, "pg_isready", "-U", DEFAULT_DB_USER]
            )
            if health.returncode == 0:
                return ClassifiedState(ServiceState.HEALTHY, "pg_isready OK")
            return ClassifiedState(ServiceState.UNHEALTHY_OWNED, "pg_isready failed")
        detail = f"PID {listener.pid}"
        return ClassifiedState(ServiceState.FOREIGN, detail)

    if db_status.exists and not db_status.running:
        return ClassifiedState(ServiceState.STOPPED_OWNED, "container exists but stopped")
    if db_status.exists and db_status.running:
        return ClassifiedState(ServiceState.UNHEALTHY_OWNED, "container running but port unavailable")
    return ClassifiedState(ServiceState.MISSING, "container missing")


def classify_native(service_key: str, services: dict[str, Any]) -> ClassifiedState:
    """Classify API or frontend according to ownership and health."""

    service = services[service_key]
    process = get_port_process(service.port)
    if process is None:
        if check_port(service.port):
            return ClassifiedState(ServiceState.MISSING, "listener found without discoverable PID")
        return ClassifiedState(ServiceState.MISSING, f"port {service.port} not listening")

    if not determine_ownership(process.pid, service.ownership_patterns):
        return ClassifiedState(ServiceState.FOREIGN, f"PID {process.pid}")

    if not service.health_url:
        return ClassifiedState(ServiceState.HEALTHY, f"PID {process.pid}, no health URL")

    code = check_http_health(service.health_url, timeout=5.0)
    if code == 200:
        return ClassifiedState(ServiceState.HEALTHY, f"PID {process.pid}, HTTP 200")
    return ClassifiedState(ServiceState.UNHEALTHY_OWNED, f"PID {process.pid}, HTTP {code}")


def wait_for_database_ready(container_tool: str, services: dict[str, Any], logger: Logger) -> bool:
    """Wait for pg_isready up to configured timeout."""

    timeout = services["db"].ready_timeout_seconds
    elapsed = 0
    while elapsed < timeout:
        result = run_command(
            [container_tool, "exec", DEFAULT_CONTAINER_NAME, "pg_isready", "-U", DEFAULT_DB_USER]
        )
        if result.returncode == 0:
            logger.ok(f"PostgreSQL (port {services['db'].port}) ready [{elapsed}s]")
            return True
        wait_seconds(2)
        elapsed += 2

    logger.fail(f"PostgreSQL readiness timed out after {timeout}s")
    return False


def start_database(container_tool: str | None, services: dict[str, Any], logger: Logger) -> bool:
    """Start or create database container as needed."""

    state = classify_database(container_tool, services)
    db_port = services["db"].port

    if state.state is ServiceState.HEALTHY:
        logger.ok(f"PostgreSQL (port {db_port}) healthy ({state.detail})")
        return True

    if state.state is ServiceState.FOREIGN:
        report_foreign("PostgreSQL", db_port, logger)
        return False

    if container_tool is None:
        logger.fail("PostgreSQL requires podman or docker, but neither was found")
        return False

    if state.state is ServiceState.STOPPED_OWNED:
        logger.info("PostgreSQL starting existing container")
        result = run_command([container_tool, "start", DEFAULT_CONTAINER_NAME])
        if result.returncode != 0:
            detail = result.stderr.strip()[:200] if result.stderr else "no details"
            logger.fail(f"PostgreSQL failed to start existing container: {detail}")
            return False
        return wait_for_database_ready(container_tool, services, logger)

    if state.state is ServiceState.UNHEALTHY_OWNED:
        logger.info(f"PostgreSQL restarting ({state.detail})")
        run_command([container_tool, "stop", DEFAULT_CONTAINER_NAME])
        result = run_command([container_tool, "start", DEFAULT_CONTAINER_NAME])
        if result.returncode != 0:
            detail = result.stderr.strip()[:200] if result.stderr else "no details"
            logger.fail(f"PostgreSQL failed to restart container: {detail}")
            return False
        return wait_for_database_ready(container_tool, services, logger)

    logger.info("PostgreSQL creating new container")
    result = run_command(
        [
            container_tool,
            "run",
            "-d",
            "--name",
            DEFAULT_CONTAINER_NAME,
            "-e",
            f"POSTGRES_DB={DEFAULT_DB_NAME}",
            "-e",
            f"POSTGRES_USER={DEFAULT_DB_USER}",
            "-e",
            f"POSTGRES_PASSWORD={DEFAULT_DB_PASSWORD}",
            "-p",
            f"{db_port}:5432",
            DEFAULT_CONTAINER_IMAGE,
        ]
    )
    if result.returncode != 0:
        detail = result.stderr.strip()[:200] if result.stderr else "no details"
        logger.fail(f"PostgreSQL failed to create container: {detail}")
        return False
    return wait_for_database_ready(container_tool, services, logger)


def _spawn_background(command: list[str], cwd: Path) -> subprocess.Popen[str]:
    """Launch detached process with output suppressed."""

    return subprocess.Popen(
        command,
        cwd=str(cwd),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )


def launch_api(api_dir: Path, services: dict[str, Any], logger: Logger) -> bool:
    """Launch API and wait for health endpoint."""

    if not api_dir.is_dir():
        logger.fail(f"API directory not found: {api_dir}")
        return False

    gradle_wrapper = str(api_dir / ("gradlew.bat" if sys.platform.startswith("win") else "gradlew"))
    gradle_cmd = [gradle_wrapper, "bootRun"]
    logger.info("Starting Spring Boot API")
    start_time = time.time()
    try:
        process = _spawn_background(gradle_cmd, api_dir)
    except OSError as exc:
        logger.fail(f"Failed to spawn API: {exc}")
        return False

    elapsed = 0
    timeout = services["api"].ready_timeout_seconds
    while elapsed < timeout:
        if process.poll() is not None:
            logger.fail(f"API process died during startup (PID {process.pid})")
            return False
        code = check_http_health(services["api"].health_url, timeout=5.0)
        if code == 200:
            wall = int(time.time() - start_time)
            logger.ok(f"API (port {services['api'].port}) started (PID {process.pid}) [{wall}s]")
            return True
        wait_seconds(5)
        elapsed += 5

    logger.fail(f"API health check timed out after {timeout}s")
    return False


def launch_web(web_dir: Path, services: dict[str, Any], logger: Logger) -> bool:
    """Launch frontend and wait for HTTP readiness."""

    if not web_dir.is_dir():
        logger.fail(f"Frontend directory not found: {web_dir}")
        return False

    npm_path = resolve_executable("npm")
    if npm_path is None:
        logger.fail("npm not found on PATH (expected npm or npm.cmd)")
        return False

    logger.info("Starting Angular frontend")
    start_time = time.time()
    try:
        process = _spawn_background([npm_path, "start"], web_dir)
    except OSError as exc:
        logger.fail(f"Failed to spawn frontend: {exc}")
        return False

    elapsed = 0
    timeout = services["web"].ready_timeout_seconds
    while elapsed < timeout:
        if process.poll() is not None:
            logger.fail(f"Frontend process died during startup (PID {process.pid})")
            return False
        code = check_http_health(services["web"].health_url, timeout=5.0)
        if code == 200:
            wall = int(time.time() - start_time)
            logger.ok(f"Frontend (port {services['web'].port}) started (PID {process.pid}) [{wall}s]")
            return True
        wait_seconds(5)
        elapsed += 5

    logger.fail(f"Frontend health check timed out after {timeout}s")
    return False


def restart_native(service_key: str, directory: Path, services: dict[str, Any], logger: Logger) -> bool:
    """Stop service listeners and relaunch process."""

    service = services[service_key]
    for proc in get_port_processes(service.port):
        terminate_pid(proc.pid, service.display_name, logger)

    if service_key == "api":
        for proc in psutil.process_iter(attrs=["pid", "cmdline"]):
            cmdline = " ".join(proc.info.get("cmdline") or [])
            if "gradlew" in cmdline and "bootRun" in cmdline:
                terminate_pid(proc.pid, "Gradle wrapper", logger)
        return launch_api(directory, services, logger)

    return launch_web(directory, services, logger)


def reconcile_native(service_key: str, directory: Path, services: dict[str, Any], logger: Logger) -> bool:
    """Reconcile native service according to classification state."""

    service = services[service_key]
    state = classify_native(service_key, services)

    if state.state is ServiceState.HEALTHY:
        logger.ok(f"{service.display_name} (port {service.port}) healthy ({state.detail})")
        return True
    if state.state is ServiceState.MISSING:
        return launch_api(directory, services, logger) if service_key == "api" else launch_web(
            directory,
            services,
            logger,
        )
    if state.state is ServiceState.UNHEALTHY_OWNED:
        logger.info(f"{service.display_name} restarting ({state.detail})")
        return restart_native(service_key, directory, services, logger)

    report_foreign(service.display_name, service.port, logger)
    return False


def stop_native_port(port: int, label: str, logger: Logger, force: bool) -> None:
    """Stop all listener processes on a given port."""

    processes = get_port_processes(port)
    if not processes:
        logger.skip(f"{label} (port {port}) not running")
        return
    for proc in processes:
        terminate_pid(proc.pid, label, logger, force=force)
    logger.ok(f"{label} (port {port}) stopped")


def stop_database(container_tool: str | None, logger: Logger, force: bool) -> None:
    """Stop database container without removing data."""

    if not container_tool:
        logger.skip("Database skipped (no container runtime found)")
        return

    status = inspect_container(container_tool, DEFAULT_CONTAINER_NAME)
    if not status.exists or not status.running:
        logger.skip(f"PostgreSQL ({DEFAULT_CONTAINER_NAME}) not running")
        return

    command = [container_tool, "stop", "-t", "0", DEFAULT_CONTAINER_NAME] if force else [
        container_tool,
        "stop",
        DEFAULT_CONTAINER_NAME,
    ]
    result = run_command(command)
    if result.returncode == 0:
        logger.ok(f"PostgreSQL ({DEFAULT_CONTAINER_NAME}) stopped (data preserved)")
    else:
        logger.fail("PostgreSQL failed to stop")


def stop_stack(services: dict[str, Any], logger: Logger, force: bool = False) -> int:
    """Stop frontend, then API, then DB."""

    logger.info("Stopping services")
    stop_native_port(services["web"].port, "Frontend", logger, force=force)
    stop_native_port(services["api"].port, "API", logger, force=force)

    for proc in psutil.process_iter(attrs=["pid", "cmdline"]):
        cmdline = " ".join(proc.info.get("cmdline") or [])
        if "gradlew" in cmdline and "bootRun" in cmdline:
            terminate_pid(proc.pid, "Gradle wrapper", logger, force=force)

    stop_database(detect_container_tool(), logger, force=force)
    logger.info("Shutdown complete")
    return 1 if logger.had_failures else 0


def ensure_podman_machine_ready(logger: Logger) -> bool:
    """Ensure Podman machine exists and is running on platforms that require it."""

    runtime = detect_container_tool()
    if runtime != "podman":
        return True

    list_result = run_command(["podman", "machine", "list", "--format", "json"])
    if list_result.returncode != 0:
        # Native Podman on Linux does not always provide podman machine.
        return True

    try:
        machines = json.loads(list_result.stdout or "[]")
    except json.JSONDecodeError:
        logger.fail("Unable to parse podman machine list output")
        return False

    if not isinstance(machines, list) or not machines:
        logger.fail("No Podman machine found. Run: podman machine init && podman machine start")
        return False

    running_machine = next(
        (
            machine
            for machine in machines
            if isinstance(machine, dict) and bool(machine.get("Running"))
        ),
        None,
    )
    if running_machine is not None:
        return True

    first_machine = next((machine for machine in machines if isinstance(machine, dict)), None)
    if first_machine is None:
        logger.fail("No valid Podman machine entries found in machine list output")
        return False

    machine_name = str(first_machine.get("Name") or "<unknown>")
    logger.info(f"Starting Podman machine '{machine_name}'")
    start_result = run_command(["podman", "machine", "start", machine_name])
    if start_result.returncode != 0:
        detail = start_result.stderr.strip()[:200] if start_result.stderr else "no details"
        logger.fail(f"Failed to start Podman machine '{machine_name}': {detail}")
        return False
    logger.ok(f"Podman machine '{machine_name}' is running")
    return True


def start_stack(
    services: dict[str, Any],
    logger: Logger,
    api_dir: Path,
    web_dir: Path,
    fresh: bool = False,
) -> int:
    """Reconcile DB -> API -> frontend."""

    if fresh:
        logger.info("Fresh start requested; stopping stack before startup")
        stop_stack(services, Logger("[dev-stop]"), force=False)
        print("")

    logger.info("Reconciling services")
    container_tool = detect_container_tool()
    if container_tool == "podman":
        if not ensure_podman_machine_ready(logger):
            logger.fail("Cannot proceed without container runtime")
            return 1
    db_ok = start_database(container_tool, services, logger)

    if db_ok:
        reconcile_native("api", api_dir, services, logger)
    else:
        logger.fail("API skipped (database not ready)")

    reconcile_native("web", web_dir, services, logger)

    if logger.had_failures:
        logger.fail("Some services failed to start")
        return 1
    logger.ok("All services ready")
    return 0


def status_records(services: dict[str, Any], check_health: bool) -> list[dict[str, Any]]:
    """Collect status records for services and database container."""

    records: list[dict[str, Any]] = []
    for key in ("api", "web", "db"):
        service = services[key]
        proc = get_port_process(service.port)
        status = "running" if proc is not None or check_port(service.port) else "stopped"
        health = "-"
        if check_health and service.health_url:
            code = check_http_health(service.health_url, timeout=5.0)
            health = "OK" if code in (200, 204) else ("DOWN" if code == 0 else f"WARN ({code})")

        records.append(
            {
                "id": service.id,
                "name": service.display_name,
                "type": "native" if key != "db" else "container-port",
                "port": service.port,
                "status": status,
                "pid": proc.pid if proc else None,
                "process": proc.name if proc else "",
                "health": health,
                "healthUrl": service.health_url or "",
                "source": "port-scan",
            }
        )

    container_tool = detect_container_tool()
    container_status: ContainerStatus = inspect_container(container_tool, DEFAULT_CONTAINER_NAME)
    records.append(
        {
            "id": DEFAULT_CONTAINER_NAME,
            "name": "PostgreSQL container",
            "type": "container",
            "port": services["db"].port,
            "status": "running" if container_status.running else ("stopped" if container_status.exists else "missing"),
            "pid": None,
            "process": container_tool or "",
            "health": "-",
            "healthUrl": "",
            "portMappings": container_status.port_mappings,
            "source": container_tool or "none",
        }
    )

    return records


def render_markdown(records: list[dict[str, Any]]) -> None:
    """Render status in markdown table format."""

    print("## Development Environment Status")
    print("")
    print("| Service | Type | Port | Status | PID | Process | Health | Port Mappings |")
    print("|---------|------|------|--------|-----|---------|--------|---------------|")
    for record in records:
        print(
            f"| {record['name']} | {record['type']} | {record.get('port', '-') or '-'} | "
            f"{record['status']} | {record.get('pid', '-') or '-'} | {record.get('process', '-') or '-'} | "
            f"{record.get('health', '-')} | {record.get('portMappings', '-') or '-'} |"
        )


def render_text(records: list[dict[str, Any]]) -> None:
    """Render status in human-readable text format."""

    print("Development Environment Status")
    print("==============================")
    for record in records:
        print(
            f"{record['name']} ({record['type']}) - port {record.get('port', '-')}: "
            f"{record['status']} | pid: {record.get('pid', '-') or '-'} | "
            f"process: {record.get('process', '-') or '-'} | health: {record.get('health', '-')}"
        )
        if record.get("portMappings"):
            print(f"  port mappings: {record['portMappings']}")


def render_json(records: list[dict[str, Any]]) -> None:
    """Render status as JSON."""

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "containerRuntime": detect_container_tool() or "none",
        "services": records,
    }
    print(json.dumps(payload, indent=2))


def build_parser() -> argparse.ArgumentParser:
    """Create CLI parser with subcommands."""

    parser = argparse.ArgumentParser(
        prog="dev-stack.py",
        description="Unified procurement development stack controller",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    start_parser = subparsers.add_parser("start", help="Start stack with reconciler behavior")
    start_parser.add_argument("--fresh", action="store_true", help="Stop stack before start")
    start_parser.add_argument("--api-dir", type=Path, default=derive_default_api_dir(), help="API directory path")
    start_parser.add_argument("--web-dir", type=Path, default=derive_default_web_dir(), help="Frontend directory path")

    stop_parser = subparsers.add_parser("stop", help="Stop stack gracefully")
    stop_parser.add_argument("--force", action="store_true", help="Force immediate kills")

    status_parser = subparsers.add_parser("status", help="Print stack diagnostics")
    status_parser.add_argument(
        "--format",
        choices=("text", "json", "markdown"),
        default="markdown",
        help="Output format",
    )
    status_parser.add_argument(
        "--check-health",
        action="store_true",
        help="Perform HTTP health checks for services with URLs",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Program entrypoint."""

    parser = build_parser()
    args = parser.parse_args(argv)
    services = build_service_definitions()

    if args.command == "start":
        return start_stack(
            services=services,
            logger=Logger("[dev-start]"),
            api_dir=args.api_dir,
            web_dir=args.web_dir,
            fresh=args.fresh,
        )
    if args.command == "stop":
        return stop_stack(services=services, logger=Logger("[dev-stop]"), force=args.force)

    records = status_records(services=services, check_health=args.check_health)
    if args.format == "json":
        render_json(records)
    elif args.format == "text":
        render_text(records)
    else:
        render_markdown(records)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(1)
