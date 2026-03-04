#!/usr/bin/env python3
"""
Description: Count lines, functions, classes, and modules in codebase
Usage: 843-count-entities.py [directory]
"""

import subprocess
import sys
from pathlib import Path


def check_tool(tool_name: str) -> None:
    """
    Check if required tool is available.

    Args:
        tool_name: Name of the tool to check (e.g., 'rg', 'fd')

    Exits:
        sys.exit(2) if tool is not found
    """
    try:
        subprocess.run([tool_name, '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"Error: {tool_name} not found. Install: cargo install {tool_name if tool_name != 'fd' else 'fd-find'}")
        sys.exit(2)

def get_python_files_fd(directory: str) -> list:
    """
    Get all Python files using fd (respects .gitignore).

    Args:
        directory: Directory path to search

    Returns:
        List of Python file paths (empty list on error)
    """
    try:
        result = subprocess.run(
            ['fd', '--type', 'f', '--extension', 'py', '.', directory],
            capture_output=True,
            text=True,
            check=True
        )
        return [f for f in result.stdout.strip().split('\n') if f]
    except subprocess.CalledProcessError:
        return []

def count_entities_rg(filepath: str) -> dict:
    """
    Count functions, classes, and lines in a Python file using ripgrep.

    Args:
        filepath: Path to Python file

    Returns:
        Dictionary with keys: 'lines', 'functions', 'classes'
        All values default to 0 on error
    """
    try:
        # Count function definitions
        # rg --count returns "filepath:count" or empty if no matches
        func_result = subprocess.run(
            ['rg', '--count', r'^def ', filepath],
            capture_output=True,
            text=True
        )
        func_count = 0
        if func_result.stdout.strip():
            # Parse "filepath:count" format
            parts = func_result.stdout.strip().split(':')
            if len(parts) >= 2:
                try:
                    func_count = int(parts[-1])
                except (ValueError, IndexError):
                    func_count = 0

        # Count class definitions
        class_result = subprocess.run(
            ['rg', '--count', r'^class ', filepath],
            capture_output=True,
            text=True
        )
        class_count = 0
        if class_result.stdout.strip():
            # Parse "filepath:count" format
            parts = class_result.stdout.strip().split(':')
            if len(parts) >= 2:
                try:
                    class_count = int(parts[-1])
                except (ValueError, IndexError):
                    class_count = 0

        # Count lines
        with open(filepath, encoding='utf-8', errors='ignore') as f:
            lines = len(f.readlines())

        return {'lines': lines, 'functions': func_count, 'classes': class_count}
    except Exception:
        return {'lines': 0, 'functions': 0, 'classes': 0}

def main():
    if len(sys.argv) < 2:
        print("Usage: 843-count-entities.py [directory]")
        print("\nExample:")
        print("  python 843-count-entities.py src/backend")
        sys.exit(2)

    directory = sys.argv[1]

    if not Path(directory).exists():
        print(f"Error: Directory {directory} not found")
        sys.exit(2)

    # Check for required tools
    check_tool('fd')
    check_tool('rg')

    print("Codebase Metrics")

    # Get Python files using fd (fast, respects .gitignore)
    python_files = get_python_files_fd(directory)

    if not python_files:
        print("No Python files found")
        sys.exit(1)

    total_lines = 0
    total_functions = 0
    total_classes = 0
    module_stats = []

    for py_file in python_files:
        result = count_entities_rg(py_file)
        total_lines += result['lines']
        total_functions += result['functions']
        total_classes += result['classes']

        # Only track significant files (configurable threshold)
        MIN_LINES_FOR_TRACKING = 100
        if result['lines'] > MIN_LINES_FOR_TRACKING:
            module_stats.append({
                'file': py_file,
                'lines': result['lines'],
                'functions': result['functions'],
                'classes': result['classes']
            })

    print(f"Files: {len(python_files)}, Lines: {total_lines:,}, Functions: {total_functions}, Classes: {total_classes}")

    print("Top modules by size:")
    for stat in sorted(module_stats, key=lambda x: x['lines'], reverse=True)[:10]:
        print(f"{stat['file']}: {stat['lines']} lines, {stat['functions']} fns, {stat['classes']} classes")

    avg_module_size = total_lines // len(python_files) if python_files else 0
    LARGE_MODULE_THRESHOLD = 800  # Lines threshold for "large module" classification
    large_modules = sum(1 for s in module_stats if s['lines'] > LARGE_MODULE_THRESHOLD)
    avg_functions = total_functions / len(python_files) if python_files else 0

    print(f"Avg module: {avg_module_size} lines, {avg_functions:.1f} fns. Large modules (>{LARGE_MODULE_THRESHOLD}): {large_modules}")

    sys.exit(0)

if __name__ == "__main__":
    main()
