# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

"""
Audit a Rust workspace against rust-development skill mandates.

Usage:
    uv run --script scripts/audit-rust-project.py --workspace /path/to/project
    uv run --script scripts/audit-rust-project.py --workspace .
"""

from __future__ import annotations

import argparse
import glob
import os
import re
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

EXIT_SUCCESS = 0

PASS_ICON = "✓"
WARN_ICON = "⚠"
INFO_ICON = "ℹ"

CLONE_HOTSPOT_THRESHOLD = 15
CLONE_TOP_LIMIT = 5
PANIC_TOP_LIMIT = 3
CFG_TEST_PATTERN = re.compile(r"^\s*#\s*\[\s*cfg\s*\(\s*test\s*\)\s*\]")


@dataclass(slots=True)
class CheckResult:
    icon: str
    headline: str
    details: list[str] = field(default_factory=list)
    passed: bool = False
    recommendation: bool = False


@dataclass(slots=True)
class RustFileStats:
    path: Path
    clone_count: int
    unwrap_count: int
    expect_without_invariant_count: int
    mutex_connection_lines: list[int]

    @property
    def panic_count(self) -> int:
        return self.unwrap_count + self.expect_without_invariant_count


@dataclass(slots=True)
class AuditArgs:
    workspace: Path | None


def parse_args(argv: list[str]) -> AuditArgs:
    parser = argparse.ArgumentParser(
        prog="audit-rust-project.py",
        description="Audit a Rust workspace against rust-development skill mandates.",
        add_help=True,
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        help="Path to the Cargo workspace root.",
    )
    namespace = parser.parse_args(argv)
    return AuditArgs(workspace=getattr(namespace, "workspace", None))


def main(argv: list[str] | None = None) -> int:
    configure_output()
    args = parse_args(sys.argv[1:] if argv is None else argv)

    if args.workspace is None:
        print_report_header(Path(".").resolve())
        emit_result(
            CheckResult(
                icon=WARN_ICON,
                headline="Missing required --workspace argument",
                details=["Run: uv run --script scripts/audit-rust-project.py --workspace /path/to/project"],
                recommendation=True,
            )
        )
        emit_summary([CheckResult(icon="", headline="", recommendation=True)])
        return EXIT_SUCCESS

    workspace = args.workspace.expanduser().resolve()
    print_report_header(workspace)

    try:
        results = audit_workspace(workspace)
    except Exception as exc:  # noqa: BLE001
        results = [
            CheckResult(
                icon=WARN_ICON,
                headline="Audit failed before completion",
                details=[str(exc)],
                recommendation=True,
            )
        ]

    for result in results:
        emit_result(result)
    emit_summary(results)
    return EXIT_SUCCESS


def print_report_header(workspace: Path) -> None:
    emit(f"Rust Project Audit: {workspace}")
    emit("=====================================")


def audit_workspace(workspace: Path) -> list[CheckResult]:
    workspace_data, members, error = load_workspace(workspace)
    if error is not None:
        return [error]

    assert workspace_data is not None

    results: list[CheckResult] = [
        check_cargo_config(workspace),
        check_profiles(workspace_data),
        check_workspace_lints(workspace_data),
    ]

    edition_results = check_member_editions(workspace, workspace_data, members)
    results.extend(edition_results)
    results.append(check_lint_inheritance(workspace, members))

    all_rust_files = list(iter_rust_files(workspace))
    production_rust_files = list(iter_rust_files(workspace, skip_tests=True))
    clone_stats = [scan_clone_density(workspace, path) for path in all_rust_files]
    panic_stats = [scan_non_test_panic_patterns(workspace, path) for path in production_rust_files]
    mutex_stats = [scan_mutex_connection(workspace, path) for path in all_rust_files]

    results.append(check_clone_density(clone_stats))
    results.append(check_panic_patterns(panic_stats))
    results.append(check_mutex_connection_pattern(mutex_stats))

    windows_result = check_windows_defender_advisory()
    if windows_result is not None:
        results.append(windows_result)

    return results


def load_workspace(
    workspace: Path,
) -> tuple[dict[str, Any] | None, list[Path], CheckResult | None]:
    if not workspace.exists():
        return None, [], CheckResult(
            icon=WARN_ICON,
            headline=f"Workspace path does not exist: {workspace}",
            details=["Pass --workspace a directory containing Cargo.toml."],
            recommendation=True,
        )

    cargo_toml = workspace / "Cargo.toml"
    if not cargo_toml.is_file():
        return None, [], CheckResult(
            icon=WARN_ICON,
            headline="Workspace Cargo.toml missing",
            details=[f"Expected: {cargo_toml}"],
            recommendation=True,
        )

    data, parse_error = load_toml(cargo_toml)
    if parse_error is not None:
        return None, [], CheckResult(
            icon=WARN_ICON,
            headline="Workspace Cargo.toml could not be parsed",
            details=[parse_error],
            recommendation=True,
        )

    workspace_table = as_table(data.get("workspace"))
    members_value = workspace_table.get("members")
    if not isinstance(members_value, list) or not all(isinstance(item, str) for item in members_value):
        return data, [], CheckResult(
            icon=WARN_ICON,
            headline="Workspace members missing from Cargo.toml",
            details=['Add [workspace] members = ["crate-path"]'],
            recommendation=True,
        )

    members = resolve_member_manifests(workspace, members_value)
    return data, members, None


def load_toml(path: Path) -> tuple[dict[str, Any], str | None]:
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        return {}, f"{path}: TOML parse error: {exc}"
    except OSError as exc:
        return {}, f"{path}: {exc}"

    if not isinstance(data, dict):
        return {}, f"{path}: top-level TOML document is not a table"
    return data, None


def resolve_member_manifests(workspace: Path, members: list[str]) -> list[Path]:
    manifests: set[Path] = set()
    for member in members:
        matches = glob.glob(member, root_dir=workspace, recursive=True)
        if not matches:
            matches = [member]
        for match in matches:
            manifest_path = (workspace / match / "Cargo.toml").resolve()
            if manifest_path.is_file():
                manifests.add(manifest_path)
    return sorted(manifests)


def check_cargo_config(workspace: Path) -> CheckResult:
    config_path = workspace / ".cargo" / "config.toml"
    if config_path.is_file():
        return CheckResult(
            icon=PASS_ICON,
            headline=".cargo/config.toml present",
            passed=True,
        )
    return CheckResult(
        icon=WARN_ICON,
        headline=".cargo/config.toml missing",
        details=["Add .cargo/config.toml at the workspace root"],
        recommendation=True,
    )


def check_profiles(workspace_data: dict[str, Any]) -> CheckResult:
    profiles = as_table(workspace_data.get("profile"))
    dev_profile = as_table(profiles.get("dev"))
    release_profile = as_table(profiles.get("release"))

    missing: list[str] = []
    if not dev_profile:
        missing.append("[profile.dev]")
    if not release_profile:
        missing.append("[profile.release]")
    elif "lto" not in release_profile:
        missing.append("[profile.release].lto")

    if not missing:
        return CheckResult(
            icon=PASS_ICON,
            headline="Dev and release profile overrides configured",
            passed=True,
        )

    return CheckResult(
        icon=WARN_ICON,
        headline="Workspace profile overrides incomplete",
        details=["Add missing entries to Cargo.toml: " + ", ".join(missing)],
        recommendation=True,
    )


def check_workspace_lints(workspace_data: dict[str, Any]) -> CheckResult:
    workspace_table = as_table(workspace_data.get("workspace"))
    workspace_lints = as_table(workspace_table.get("lints"))
    clippy_lints = as_table(workspace_lints.get("clippy"))

    if clippy_lints and "dbg_macro" in clippy_lints:
        return CheckResult(
            icon=PASS_ICON,
            headline="Workspace lint configuration configured",
            passed=True,
        )

    return CheckResult(
        icon=WARN_ICON,
        headline="Workspace lint configuration missing",
        details=["Add [workspace.lints.clippy] with dbg_macro configured in Cargo.toml"],
        recommendation=True,
    )


def check_member_editions(
    workspace: Path,
    workspace_data: dict[str, Any],
    members: list[Path],
) -> list[CheckResult]:
    if not members:
        return [
            CheckResult(
                icon=WARN_ICON,
                headline="No member crates resolved from workspace members",
                details=["Check [workspace].members globs in Cargo.toml"],
                recommendation=True,
            )
        ]

    edition_2021: list[str] = []
    legacy_or_missing: list[str] = []

    for manifest_path in members:
        manifest_data, parse_error = load_toml(manifest_path)
        crate_name = crate_name_for_manifest(workspace, manifest_path, manifest_data)
        if parse_error is not None:
            legacy_or_missing.append(f"{crate_name} (unreadable manifest)")
            continue

        edition = resolve_edition(workspace_data, manifest_data)
        if edition == "2024":
            continue
        if edition == "2021":
            edition_2021.append(crate_name)
            continue
        if edition is None:
            legacy_or_missing.append(f"{crate_name} (edition missing)")
            continue
        legacy_or_missing.append(f"{crate_name} ({edition})")

    results: list[CheckResult] = []

    if legacy_or_missing:
        results.append(
            CheckResult(
                icon=WARN_ICON,
                headline="Member crates with edition 2018 or older, or missing edition",
                details=["Set edition = \"2024\" or at least \"2021\" in: " + ", ".join(sorted(legacy_or_missing))],
                recommendation=True,
            )
        )
    elif not edition_2021:
        results.append(
            CheckResult(
                icon=PASS_ICON,
                headline="All member crates use edition 2024",
                passed=True,
            )
        )

    if edition_2021:
        results.append(
            CheckResult(
                icon=INFO_ICON,
                headline=f"{len(edition_2021)} member crate(s) still on edition 2021",
                details=["Consider edition 2024 for: " + ", ".join(sorted(edition_2021))],
            )
        )
        if not legacy_or_missing:
            results.insert(
                0,
                CheckResult(
                    icon=PASS_ICON,
                    headline="All member crates: edition 2021+",
                    passed=True,
                ),
            )

    return results


def check_lint_inheritance(workspace: Path, members: list[Path]) -> CheckResult:
    if not members:
        return CheckResult(
            icon=WARN_ICON,
            headline="Unable to check lint inheritance without resolved member crates",
            details=["Fix [workspace].members resolution first"],
            recommendation=True,
        )

    missing: list[str] = []
    unreadable: list[str] = []

    for manifest_path in members:
        manifest_data, parse_error = load_toml(manifest_path)
        crate_name = crate_name_for_manifest(workspace, manifest_path, manifest_data)
        if parse_error is not None:
            unreadable.append(crate_name)
            continue
        lints = as_table(manifest_data.get("lints"))
        if lints.get("workspace") is not True:
            missing.append(crate_name)

    if not missing and not unreadable:
        return CheckResult(
            icon=PASS_ICON,
            headline="All member crates inherit workspace lints",
            passed=True,
        )

    details: list[str] = []
    if missing:
        details.append("Add [lints] workspace = true to: " + ", ".join(sorted(missing)))
    if unreadable:
        details.append("Could not read Cargo.toml for: " + ", ".join(sorted(unreadable)))

    return CheckResult(
        icon=WARN_ICON,
        headline=f"{len(missing)} member crate(s) missing lint inheritance",
        details=details,
        recommendation=True,
    )


def check_clone_density(stats: list[RustFileStats]) -> CheckResult:
    if not stats:
        return CheckResult(
            icon=INFO_ICON,
            headline="No .rs files found for clone density analysis",
        )

    hotspots = [item for item in sorted(stats, key=lambda item: item.clone_count, reverse=True) if item.clone_count > CLONE_HOTSPOT_THRESHOLD]
    if not hotspots:
        return CheckResult(
            icon=PASS_ICON,
            headline="No clone hotspots (>15 per file)",
            passed=True,
        )

    details = [f"{item.path.as_posix()}: {item.clone_count} clones" for item in hotspots[:CLONE_TOP_LIMIT]]
    return CheckResult(
        icon=WARN_ICON,
        headline="Clone hotspots (>15 per file)",
        details=details,
        recommendation=True,
    )


def check_panic_patterns(stats: list[RustFileStats]) -> CheckResult:
    unwrap_total = sum(item.unwrap_count for item in stats)
    expect_total = sum(item.expect_without_invariant_count for item in stats)

    if unwrap_total == 0 and expect_total == 0:
        return CheckResult(
            icon=PASS_ICON,
            headline='No unwrap() or expect() without "invariant:" found in production code',
            passed=True,
        )

    ranked = sorted(
        (item for item in stats if item.panic_count > 0),
        key=lambda item: item.panic_count,
        reverse=True,
    )
    details = [
        f"unwrap(): {unwrap_total}, expect() without \"invariant:\": {expect_total}",
        "Top files: " + ", ".join(
            f"{item.path.as_posix()} ({item.panic_count})" for item in ranked[:PANIC_TOP_LIMIT]
        ),
    ]
    return CheckResult(
        icon=WARN_ICON,
        headline='unwrap()/expect() without invariant prefix found in production code',
        details=details,
        recommendation=True,
    )


def check_mutex_connection_pattern(stats: list[RustFileStats]) -> CheckResult:
    occurrences: list[str] = []
    for item in stats:
        for line_number in item.mutex_connection_lines:
            occurrences.append(f"{item.path.as_posix()}:{line_number}")

    if not occurrences:
        return CheckResult(
            icon=PASS_ICON,
            headline="No Mutex<Connection> patterns detected",
            passed=True,
        )

    details = occurrences.copy()
    details.append("Consider deadpool-sqlite pool")
    return CheckResult(
        icon=WARN_ICON,
        headline=f"Mutex<Connection> pattern detected in {len(occurrences)} location(s)",
        details=details,
        recommendation=True,
    )


def check_windows_defender_advisory() -> CheckResult | None:
    if sys.platform != "win32":
        return None

    appdata = os.environ.get("APPDATA")
    if not appdata:
        return CheckResult(
            icon=INFO_ICON,
            headline="Windows: ensure project dir is excluded from Defender scanning",
        )

    defender_dir = Path(appdata) / "Microsoft" / "Windows Defender"
    try:
        _ = list(defender_dir.iterdir()) if defender_dir.exists() else []
    except OSError:
        pass

    return CheckResult(
        icon=INFO_ICON,
        headline="Windows: ensure project dir is excluded from Defender scanning",
    )


def scan_clone_density(workspace: Path, path: Path) -> RustFileStats:
    text = read_text(path)
    return RustFileStats(
        path=relative_to_workspace(workspace, path),
        clone_count=text.count(".clone()"),
        unwrap_count=0,
        expect_without_invariant_count=0,
        mutex_connection_lines=[],
    )


def scan_non_test_panic_patterns(workspace: Path, path: Path) -> RustFileStats:
    text = strip_cfg_test_blocks(read_text(path))
    unwrap_count = text.count(".unwrap()")
    expect_without_invariant_count = count_expect_without_invariant(text)
    return RustFileStats(
        path=relative_to_workspace(workspace, path),
        clone_count=0,
        unwrap_count=unwrap_count,
        expect_without_invariant_count=expect_without_invariant_count,
        mutex_connection_lines=[],
    )


def scan_mutex_connection(workspace: Path, path: Path) -> RustFileStats:
    text = read_text(path)
    matches: list[int] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if "Mutex<Connection>" in line:
            matches.append(line_number)
    return RustFileStats(
        path=relative_to_workspace(workspace, path),
        clone_count=0,
        unwrap_count=0,
        expect_without_invariant_count=0,
        mutex_connection_lines=matches,
    )


def iter_rust_files(workspace: Path, *, skip_tests: bool = False) -> list[Path]:
    files: list[Path] = []
    for path in workspace.rglob("*.rs"):
        if is_in_target_dir(path):
            continue
        if skip_tests and is_test_path(path):
            continue
        files.append(path)
    return sorted(files)


def is_in_target_dir(path: Path) -> bool:
    return "target" in path.parts


def is_test_path(path: Path) -> bool:
    return "tests" in path.parts


def strip_cfg_test_blocks(text: str) -> str:
    output: list[str] = []
    skipping = False
    pending_cfg_test = False
    brace_depth = 0

    for line in text.splitlines(keepends=True):
        if skipping:
            brace_depth += line.count("{") - line.count("}")
            if brace_depth <= 0:
                skipping = False
                brace_depth = 0
            continue

        if pending_cfg_test:
            if "{" not in line:
                continue
            skipping = True
            brace_depth = line.count("{") - line.count("}")
            if brace_depth <= 0:
                skipping = False
                brace_depth = 0
            pending_cfg_test = False
            continue

        if CFG_TEST_PATTERN.match(line):
            pending_cfg_test = True
            continue

        output.append(line)

    return "".join(output)


def count_expect_without_invariant(text: str) -> int:
    count = 0
    start = 0
    needle = ".expect("

    while True:
        index = text.find(needle, start)
        if index == -1:
            return count

        argument = extract_parenthesized_argument(text, index + len(needle) - 1)
        if "invariant:" not in argument:
            count += 1
        start = index + len(needle)


def extract_parenthesized_argument(text: str, open_paren_index: int) -> str:
    depth = 0
    characters: list[str] = []

    for character in text[open_paren_index + 1 :]:
        if character == "(":
            depth += 1
        elif character == ")":
            if depth == 0:
                break
            depth -= 1
        characters.append(character)

    return "".join(characters)


def resolve_edition(workspace_data: dict[str, Any], manifest_data: dict[str, Any]) -> str | None:
    package = as_table(manifest_data.get("package"))
    edition = package.get("edition")
    if isinstance(edition, str):
        return edition

    if isinstance(edition, dict) and edition.get("workspace") is True:
        workspace_package = as_table(as_table(workspace_data.get("workspace")).get("package"))
        inherited = workspace_package.get("edition")
        if isinstance(inherited, str):
            return inherited

    return None


def crate_name_for_manifest(workspace: Path, manifest_path: Path, manifest_data: dict[str, Any]) -> str:
    package = as_table(manifest_data.get("package"))
    name = package.get("name")
    if isinstance(name, str) and name:
        return name
    try:
        return manifest_path.parent.relative_to(workspace).as_posix()
    except ValueError:
        return manifest_path.parent.as_posix()


def as_table(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def relative_to_workspace(workspace: Path, path: Path) -> Path:
    try:
        return path.relative_to(workspace)
    except ValueError:
        return path


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def configure_output() -> None:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            pass


def emit(message: str) -> None:
    sys.stdout.write(f"{message}\n")


def emit_result(result: CheckResult) -> None:
    emit(f"{result.icon} {result.headline}")
    for detail in result.details:
        emit(f"  → {detail}")


def emit_summary(results: list[CheckResult]) -> None:
    passed = sum(1 for result in results if result.passed)
    recommendations = sum(1 for result in results if result.recommendation)
    emit("")
    emit(f"Results: {passed} checks passed, {recommendations} recommendations")


if __name__ == "__main__":
    raise SystemExit(main())
