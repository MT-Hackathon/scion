#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Check for personal linter config overlays.

Detects if personal linter configs exist and reports which lint command to use.
Supports ESLint (TypeScript/JavaScript) and Ruff (Python).

Usage:
    uv run .cursor/skills/linter-integration/scripts/check-local-config.py [path]
"""

import argparse
import sys
from pathlib import Path


def check_local_configs(project_path: Path) -> dict[str, bool]:
    """Check for personal linter config files."""
    configs = {
        "eslint.config.local.js": False,
        "eslint.config.local.mjs": False,
        "ruff.local.toml": False,
    }

    for config_name in configs:
        config_path = project_path / config_name
        if config_path.exists():
            configs[config_name] = True

    return configs


def get_lint_commands(configs: dict[str, bool]) -> dict[str, str]:
    """Determine which lint commands to use based on available configs."""
    commands = {}

    # ESLint
    if configs.get("eslint.config.local.js") or configs.get("eslint.config.local.mjs"):
        commands["eslint"] = "npm run lint:strict"
        commands["eslint_note"] = "Personal ESLint config detected - using strict mode"
    else:
        commands["eslint"] = "npm run lint"
        commands["eslint_note"] = "Using team ESLint config"

    # Ruff
    if configs.get("ruff.local.toml"):
        commands["ruff"] = "ruff check --config ruff.local.toml"
        commands["ruff_note"] = "Personal Ruff config detected - using strict mode"
    else:
        commands["ruff"] = "ruff check"
        commands["ruff_note"] = "Using team Ruff config (or default)"

    return commands


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Check for personal linter config overlays for ESLint and Ruff."
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=Path.cwd(),
        type=Path,
        help="Project path to inspect (default: current working directory)",
    )

    args = parser.parse_args()
    project_path = args.path.resolve()

    if not project_path.is_dir():
        print(f"Error: {project_path} is not a directory")
        return 1

    print(f"Checking for personal linter configs in: {project_path}")
    print("-" * 60)

    configs = check_local_configs(project_path)
    commands = get_lint_commands(configs)

    # Report findings
    found_any = False
    for config_name, exists in configs.items():
        if exists:
            found_any = True
            print(f"  {config_name}: FOUND")

    if not found_any:
        print("  No personal linter configs found")

    print()
    print("Recommended commands:")
    print(f"  TypeScript/JS: {commands['eslint']}")
    print(f"    ({commands['eslint_note']})")

    # Only show Ruff if Python files exist
    python_files = list(project_path.glob("**/*.py"))
    if python_files:
        print(f"  Python: {commands['ruff']}")
        print(f"    ({commands['ruff_note']})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
