#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

"""Build and promote the Rootstock release binary to the installed location without running the NSIS installer."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

EXIT_SUCCESS = 0
EXIT_ERROR = 1

INSTALL_DIR_NAME = "Rootstock"
BINARY_NAME = "rootstock.exe"
PROCESS_NAME = "rootstock"
STOP_TIMEOUT_SECS = 5
DEFAULT_ORT_DLL_PATH = Path(
    r"C:\Users\cmb115\.ort-1.23.0\onnxruntime-win-x64-1.23.0\lib\onnxruntime.dll"
)
MODEL_CACHE_DIR_NAME = "models--Qdrant--bge-small-en-v1.5-onnx-Q"
MODEL_RESOURCE_SUBDIR = Path("models") / "bge-small-en-v1.5-q"
MODEL_FILE_NAMES = (
    "config.json",
    "model_optimized.onnx",
    "special_tokens_map.json",
    "tokenizer_config.json",
    "tokenizer.json",
)

# Candidate locations where cargo tauri build may place the NSIS installer.
# Tauri uses the workspace target/ dir when invoked from the workspace root,
# but older docs and some configurations use src-tauri/target/. Search both.
NSIS_SEARCH_DIRS = [
    Path("target") / "release" / "bundle" / "nsis",
    Path("src-tauri") / "target" / "release" / "bundle" / "nsis",
]


def log(message: str) -> None:
    """Emit human-readable status to stderr."""
    sys.stderr.write(f"{message}\n")
    sys.stderr.flush()


def fail(message: str) -> int:
    """Emit standardized failure message to stderr and return error exit code."""
    log(f"ERROR: {message}")
    return EXIT_ERROR


def find_workspace_root() -> Path:
    """Walk up from the script location to find the Cargo workspace root.

    Script lives at: .cursor/skills/dev-startup/scripts/promote.py
    Workspace root is 4 directories up from the script's parent.
    Falls back to CWD if the expected relative position doesn't hold.
    """
    script_dir = Path(__file__).resolve().parent
    candidate = script_dir.parent.parent.parent.parent
    if (candidate / "Cargo.toml").exists():
        return candidate
    cwd = Path.cwd()
    if (cwd / "Cargo.toml").exists():
        return cwd
    raise RuntimeError(
        "Cannot locate workspace root. "
        "Run from the repository root or ensure the script is at "
        ".cursor/skills/dev-startup/scripts/promote.py."
    )


def get_install_dir() -> Path:
    """Resolve %LocalAppData%\\Rootstock\\ from the environment."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise RuntimeError(
            "%LOCALAPPDATA% is not set. "
            "This is unexpected on Windows — ensure the environment variable is available."
        )
    return Path(local_app_data) / INSTALL_DIR_NAME


def run_command(args: list[str], *, cwd: Path, dry_run: bool, label: str) -> bool:
    """Run a subprocess command, printing what will run. Returns True on success."""
    log(f"  $ {' '.join(args)}")
    if dry_run:
        return True
    result = subprocess.run(args, cwd=cwd, check=False)
    if result.returncode != 0:
        log(f"ERROR: {label} failed (exit code {result.returncode}).")
        return False
    return True


def stage_ort_dll(workspace_root: Path, *, dry_run: bool) -> bool:
    """Copy the ORT DLL into src-tauri/resources/ so Tauri bundles it as a resource.

    The DLL is resolved from DEFAULT_ORT_DLL_PATH (the pinned local download).
    The resources/ directory is gitignored; this step is required before every
    release or package build so the app bundle contains onnxruntime.dll.
    At runtime, lib.rs resolves the resource path and sets ORT_DYLIB_PATH before
    the embedding worker initialises — no user action required.
    """
    resources_dir = workspace_root / "src-tauri" / "resources"
    dest = resources_dir / "onnxruntime.dll"

    if dry_run:
        log(f"  [dry-run] Would copy {DEFAULT_ORT_DLL_PATH} -> {dest}")
        return True

    if not DEFAULT_ORT_DLL_PATH.is_file():
        log(f"ERROR: ORT DLL not found at {DEFAULT_ORT_DLL_PATH}")
        log(
            "  Download ORT 1.23.0 from https://github.com/microsoft/onnxruntime/releases/tag/v1.23.0"
            " and extract to C:\\Users\\cmb115\\.ort-1.23.0\\"
        )
        return False

    resources_dir.mkdir(exist_ok=True)
    try:
        shutil.copy2(str(DEFAULT_ORT_DLL_PATH), str(dest))
        log(f"  Staged: {dest} ({dest.stat().st_size // 1024 // 1024} MB)")
        return True
    except OSError as exc:
        log(f"ERROR: Failed to copy ORT DLL: {exc}")
        return False


def stage_model_files(workspace_root: Path, *, dry_run: bool) -> bool:
    """Copy the bundled fastembed model files into src-tauri/resources/."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        log("ERROR: %LOCALAPPDATA% is not set; cannot locate fastembed model cache")
        return False

    snapshots_dir = (
        Path(local_app_data)
        / INSTALL_DIR_NAME
        / "models"
        / MODEL_CACHE_DIR_NAME
        / "snapshots"
    )
    if not snapshots_dir.is_dir():
        log(f"ERROR: Embedding model snapshots directory not found: {snapshots_dir}")
        return False

    snapshot_dirs = sorted(
        (path for path in snapshots_dir.iterdir() if path.is_dir()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not snapshot_dirs:
        log(f"ERROR: No embedding model snapshot found under {snapshots_dir}")
        return False

    source_dir = snapshot_dirs[0]
    dest_dir = workspace_root / "src-tauri" / "resources" / MODEL_RESOURCE_SUBDIR
    if dry_run:
        log(f"  [dry-run] Would copy model files from {source_dir} -> {dest_dir}")
        return True

    missing_files = [name for name in MODEL_FILE_NAMES if not (source_dir / name).is_file()]
    if missing_files:
        log(f"ERROR: Model snapshot is missing required files: {', '.join(missing_files)}")
        log(f"  Snapshot dir: {source_dir}")
        return False

    dest_dir.mkdir(parents=True, exist_ok=True)
    try:
        for name in MODEL_FILE_NAMES:
            shutil.copy2(str(source_dir / name), str(dest_dir / name))
        total_size_mb = sum((dest_dir / name).stat().st_size for name in MODEL_FILE_NAMES) // 1024 // 1024
        log(f"  Staged: {dest_dir} ({total_size_mb} MB)")
        return True
    except OSError as exc:
        log(f"ERROR: Failed to copy embedding model files: {exc}")
        return False


def build_frontend(workspace_root: Path, *, dry_run: bool) -> bool:
    """Run 'npm run build' in app/frontend/."""
    frontend_dir = workspace_root / "app" / "frontend"
    if not dry_run and not frontend_dir.exists():
        log(f"ERROR: Frontend directory not found: {frontend_dir}")
        return False
    return run_command(
        ["npm", "run", "build"],
        cwd=frontend_dir,
        dry_run=dry_run,
        label="Frontend build",
    )


def build_release_binary(workspace_root: Path, *, dry_run: bool) -> bool:
    """Run 'cargo tauri build --no-bundle' from the workspace root.

    Using 'cargo tauri build --no-bundle' rather than 'cargo build --release'
    because the Tauri CLI sets TAURI_ENV_DEBUG=false and other required env vars
    before invoking Cargo. Without these, tauri_build::build() sees the devUrl
    in tauri.conf.json and the WebView loads http://127.0.0.1:5173 at runtime
    instead of the embedded assets — causing ERR_CONNECTION_REFUSED in the
    installed app. --no-bundle skips NSIS packaging; the binary still lands at
    target/release/rootstock.exe as expected.
    """
    return run_command(
        ["cargo", "tauri", "build", "--no-bundle"],
        cwd=workspace_root,
        dry_run=dry_run,
        label="Cargo Tauri release build (no bundle)",
    )


def build_tauri_package(workspace_root: Path, *, dry_run: bool) -> bool:
    """Run 'cargo tauri build' to produce the full NSIS installer."""
    return run_command(
        ["cargo", "tauri", "build"],
        cwd=workspace_root,
        dry_run=dry_run,
        label="cargo tauri build",
    )


def find_nsis_installer(workspace_root: Path) -> Path | None:
    """Search known bundle output locations for the NSIS installer."""
    for candidate_dir in NSIS_SEARCH_DIRS:
        full_dir = workspace_root / candidate_dir
        if not full_dir.is_dir():
            continue
        installers = sorted(full_dir.glob("*-setup.exe"), key=lambda p: p.stat().st_mtime, reverse=True)
        if installers:
            return installers[0]
    return None


def export_installer(workspace_root: Path, *, dry_run: bool) -> bool:
    """Copy the NSIS installer from target/ to dist/ so it survives any sweep.

    target/ is cache — it can be swept at session end.
    dist/ is outside the sweep boundary and persists across sessions.
    This makes the installer durable for sharing or running later.
    """
    dist_dir = workspace_root / "dist"
    if dry_run:
        log(f"  [dry-run] Would search {[str(workspace_root / d) for d in NSIS_SEARCH_DIRS]}")
        log(f"  [dry-run] Would copy installer to {dist_dir}/")
        return True

    installer = find_nsis_installer(workspace_root)
    if installer is None:
        log("ERROR: NSIS installer not found in any expected bundle location.")
        log(f"  Searched: {[str(workspace_root / d) for d in NSIS_SEARCH_DIRS]}")
        return False

    dist_dir.mkdir(exist_ok=True)
    dest = dist_dir / installer.name
    try:
        shutil.copy2(str(installer), str(dest))
        log(f"  Exported: {dest}")
        return True
    except OSError as exc:
        log(f"ERROR: Failed to export installer: {exc}")
        return False


def verify_binary_fresh(release_binary: Path, *, start_time: float, dry_run: bool) -> bool:
    """Verify the release binary exists and is newer than when this script started."""
    if dry_run:
        log(f"  [dry-run] Would verify {release_binary} exists and is freshly built.")
        return True
    if not release_binary.exists():
        log(f"ERROR: Release binary not found after build: {release_binary}")
        return False
    mtime = release_binary.stat().st_mtime
    if mtime < start_time:
        log(
            f"ERROR: Release binary at {release_binary} is older than when this script started. "
            "The build may not have produced a new artifact."
        )
        return False
    return True


def _powershell(command: str) -> subprocess.CompletedProcess[str]:
    """Run a PowerShell command and return the result."""
    return subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True,
        text=True,
        check=False,
    )


def get_installed_pids() -> list[int]:
    """Find PIDs of rootstock processes running from the install directory.

    Uses path-based matching via PowerShell so only the installed instance
    is targeted — dev instances running from target\\debug\\ are unaffected.
    """
    result = _powershell(
        f"Get-Process -Name {PROCESS_NAME} -ErrorAction SilentlyContinue "
        f"| Where-Object {{ $_.Path -like '*\\{INSTALL_DIR_NAME}\\*' }} "
        f"| Select-Object -ExpandProperty Id"
    )
    pids: list[int] = []
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if stripped.isdigit():
            pids.append(int(stripped))
    return pids


def stop_installed_instance(*, dry_run: bool) -> bool:
    """Stop the installed rootstock process, identified by path."""
    if dry_run:
        log(f"  [dry-run] Would find PIDs of {PROCESS_NAME} running from *\\{INSTALL_DIR_NAME}\\* and stop them.")
        return True

    pids = get_installed_pids()
    if not pids:
        log("  No installed rootstock process found (already stopped).")
        return True

    log(f"  Stopping installed rootstock (PID: {', '.join(str(p) for p in pids)})...")
    _powershell(
        f"Stop-Process -Id {','.join(str(p) for p in pids)} "
        f"-Force -ErrorAction SilentlyContinue"
    )
    return True


def wait_for_exit(*, timeout: float = STOP_TIMEOUT_SECS, dry_run: bool) -> None:
    """Wait up to `timeout` seconds for the installed process to fully exit."""
    if dry_run:
        log(f"  [dry-run] Would wait up to {timeout:.0f}s for process exit.")
        return

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not get_installed_pids():
            return
        time.sleep(0.25)

    log(
        f"WARNING: Installed rootstock did not exit within {timeout:.0f}s. "
        "Proceeding — the copy may fail if the file is still locked."
    )


def copy_binary(release_binary: Path, installed_binary: Path, *, dry_run: bool) -> bool:
    """Copy the release binary to the install location."""
    log(f"  {release_binary} -> {installed_binary}")
    if dry_run:
        return True
    try:
        shutil.copy2(str(release_binary), str(installed_binary))
    except OSError as exc:
        log(f"ERROR: Failed to copy binary: {exc}")
        log("  Hint: The file may still be locked. Stop the process manually and re-run.")
        return False
    return True


def restart_installed(installed_binary: Path, *, dry_run: bool) -> bool:
    """Launch the installed binary as a detached subprocess."""
    log(f"  Launching {installed_binary}")
    if dry_run:
        return True
    env = os.environ.copy()
    ort_dll_path = Path(env.get("ORT_DYLIB_PATH", "")).expanduser() if env.get("ORT_DYLIB_PATH") else None
    if ort_dll_path is None or not ort_dll_path.is_file():
        if DEFAULT_ORT_DLL_PATH.is_file():
            env["ORT_DYLIB_PATH"] = str(DEFAULT_ORT_DLL_PATH)
        elif "ORT_DYLIB_PATH" in env and ort_dll_path is not None and not ort_dll_path.is_file():
            log(f"  ORT_DYLIB_PATH ignored because the DLL was not found: {ort_dll_path}")
    try:
        # DETACHED_PROCESS + CREATE_NEW_PROCESS_GROUP ensures the child
        # outlives this script without inheriting its console.
        subprocess.Popen(
            [str(installed_binary)],
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
            close_fds=True,
            env=env,
        )
    except OSError as exc:
        log(f"ERROR: Failed to launch {installed_binary}: {exc}")
        return False
    return True


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        prog="promote.py",
        description=(
            "Build a Rootstock release binary and promote it to the NSIS install directory "
            "(%LocalAppData%\\Rootstock\\) without running the installer. "
            "Stops the running installed instance, copies the new binary, and restarts it. "
            "Dev instances (running from target\\debug\\) are never touched."
        ),
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help=(
            "Deprecated — 'cargo tauri build --no-bundle' always runs 'npm run build' via "
            "beforeBuildCommand. This flag is kept for backward compatibility but has no effect."
        ),
    )
    parser.add_argument(
        "--build-only",
        action="store_true",
        help="Build the release binary but skip stop/copy/restart (smoke-tests the build).",
    )
    parser.add_argument(
        "--package",
        action="store_true",
        help=(
            "Run 'cargo tauri build' to produce the full NSIS installer, then export it "
            "to dist/ at the repo root. The installer in dist/ survives session sweeps. "
            "Does not promote the binary to the install directory."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without executing any commands.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Script entrypoint."""
    if sys.platform != "win32":
        log(
            "ERROR: Promote script is Windows-only. "
            "On Linux/macOS, copy the binary manually."
        )
        return EXIT_ERROR

    args = parse_args(sys.argv[1:] if argv is None else argv)
    dry_run: bool = args.dry_run

    if dry_run:
        log("[dry-run] No commands will be executed.\n")

    try:
        workspace_root = find_workspace_root()
    except RuntimeError as exc:
        return fail(str(exc))

    release_binary = workspace_root / "target" / "release" / BINARY_NAME

    try:
        install_dir = get_install_dir()
    except RuntimeError as exc:
        return fail(str(exc))

    installed_binary = install_dir / BINARY_NAME

    log(f"Workspace root : {workspace_root}")

    # --package mode: full Tauri build + export installer to dist/
    if args.package:
        log("")
        log("==> Staging ORT DLL into src-tauri/resources/...")
        if not stage_ort_dll(workspace_root, dry_run=dry_run):
            return EXIT_ERROR
        log("")
        log("==> Staging embedding model files into src-tauri/resources/...")
        if not stage_model_files(workspace_root, dry_run=dry_run):
            return EXIT_ERROR
        log("")
        log("==> Running cargo tauri build (full packaging)...")
        start_time = time.time()
        build_ok = build_tauri_package(workspace_root, dry_run=dry_run)
        # The Tauri bundler exits non-zero when TAURI_SIGNING_PRIVATE_KEY is
        # absent, even though it successfully produced the NSIS installer.
        # The installer is usable for local install without a signature — only
        # the auto-updater requires the signed artifact. Export regardless of
        # exit code; the export step will fail if the installer wasn't produced.
        if not build_ok:
            log("WARN: cargo tauri build reported an error (possibly missing signing key).")
            log("      Attempting export anyway — installer may still be present.")
        log("")
        log("==> Exporting installer to dist/ (durable across sweeps)...")
        if not export_installer(workspace_root, dry_run=dry_run):
            return EXIT_ERROR
        log("")
        if dry_run:
            print("[dry-run] Would: cargo tauri build -> export installer to dist/")
        else:
            installer = find_nsis_installer(workspace_root)
            dest = workspace_root / "dist" / (installer.name if installer else "Rootstock-setup.exe")
            print(f"OK packaged  dest={dest}")
        return EXIT_SUCCESS

    log(f"Release binary : {release_binary}")
    log(f"Install dir    : {install_dir}")
    log("")

    # Step 1 — Verify install directory exists (NSIS must have run at least once)
    if not dry_run and not install_dir.exists():
        return fail(
            f"Install directory not found: {install_dir}\n"
            "  Run the NSIS installer first to create the install directory.\n"
            "  After the initial install, use this script for subsequent updates."
        )

    start_time = time.time()

    # Step 2 — Stage ORT DLL into resources/ so Tauri bundles it
    log("==> Staging ORT DLL into src-tauri/resources/...")
    if not stage_ort_dll(workspace_root, dry_run=dry_run):
        return EXIT_ERROR
    log("")

    log("==> Staging embedding model files into src-tauri/resources/...")
    if not stage_model_files(workspace_root, dry_run=dry_run):
        return EXIT_ERROR
    log("")

    # Step 3 — Build release binary
    log("==> Building release binary...")
    if not build_release_binary(workspace_root, dry_run=dry_run):
        return EXIT_ERROR
    log("")

    # Step 4 — Verify build produced a fresh artifact
    log("==> Verifying build artifact...")
    if not verify_binary_fresh(release_binary, start_time=start_time, dry_run=dry_run):
        return EXIT_ERROR

    if args.build_only:
        log("")
        log("Build complete (--build-only: promote steps skipped).")
        print(f"OK build-only {release_binary}")
        return EXIT_SUCCESS

    # Step 5 — Stop installed instance
    log("")
    log("==> Stopping installed instance...")
    if not stop_installed_instance(dry_run=dry_run):
        return EXIT_ERROR

    # Step 6 — Wait for process to exit
    wait_for_exit(dry_run=dry_run)

    # Step 7 — Copy binary
    log("")
    log("==> Copying binary...")
    if not copy_binary(release_binary, installed_binary, dry_run=dry_run):
        return EXIT_ERROR

    # Step 8 — Restart installed binary
    log("")
    log("==> Restarting installed instance...")
    if not restart_installed(installed_binary, dry_run=dry_run):
        return EXIT_ERROR

    # Step 9 — Report success
    log("")
    if dry_run:
        print("[dry-run] Would: build -> stop installed -> copy -> restart")
    else:
        build_ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(release_binary.stat().st_mtime))
        print(f"OK promoted  built={build_ts}  dest={installed_binary}")

    return EXIT_SUCCESS


if __name__ == "__main__":
    raise SystemExit(main())
