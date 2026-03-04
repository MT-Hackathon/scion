#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Description: Analyze docstring coverage and documentation gaps by module
Usage: 832-check-docstring-coverage.py [directory]
"""

import argparse
import ast
import subprocess
import sys
from pathlib import Path
from typing import Any


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

def get_python_files_rg(directory: str) -> list:
    """
    Get all Python files using ripgrep (respects .gitignore).

    Args:
        directory: Directory path to search

    Returns:
        List of Python file paths (empty list on error)
    """
    try:
        result = subprocess.run(
            ['rg', '--files', '--type', 'py', directory],
            capture_output=True,
            text=True,
            check=True
        )
        return [f for f in result.stdout.strip().split('\n') if f]
    except subprocess.CalledProcessError:
        return []

def check_docstring(node) -> bool:
    """
    Check if an AST node has a non-empty docstring.

    Args:
        node: AST node (FunctionDef, ClassDef, etc.)

    Returns:
        True if node has a non-empty docstring, False otherwise
    """
    docstring = ast.get_docstring(node)
    return bool(docstring and docstring.strip())

def analyze_file(file_path: str) -> dict[str, Any] | None:
    """
    Analyze docstring coverage in a Python file.

    Args:
        file_path: Path to Python file to analyze

    Returns:
        Dictionary with keys: 'functions', 'functions_with_docs', 'classes',
        'classes_with_docs', 'missing' (list of tuples: name, lineno, kind)
        Returns None on parse error
    """
    try:
        with open(file_path, encoding='utf-8', errors='ignore') as f:
            tree = ast.parse(f.read())
    except Exception:
        return None

    functions = 0
    classes = 0
    functions_with_docs = 0
    classes_with_docs = 0
    missing = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith('_'):
                functions += 1
                if check_docstring(node):
                    functions_with_docs += 1
                else:
                    missing.append((node.name, node.lineno, 'function'))
        elif isinstance(node, ast.ClassDef):
            classes += 1
            if check_docstring(node):
                classes_with_docs += 1
            else:
                missing.append((node.name, node.lineno, 'class'))

    return {
        'functions': functions,
        'functions_with_docs': functions_with_docs,
        'classes': classes,
        'classes_with_docs': classes_with_docs,
        'missing': missing,
    }

def main():
    parser = argparse.ArgumentParser(
        description="Analyze docstring coverage and identify documentation gaps by module."
    )
    parser.add_argument("directory", help="Directory path to scan for Python files")

    args = parser.parse_args()

    directory = args.directory

    if not Path(directory).exists():
        print(f"Error: Directory {directory} not found")
        sys.exit(2)

    # Check for ripgrep
    check_tool('rg')

    python_files = get_python_files_rg(directory)
    if not python_files:
        print("No Python files found")
        sys.exit(1)

    total_functions = 0
    total_functions_with_docs = 0
    total_classes = 0
    total_classes_with_docs = 0
    modules_with_gaps = []

    print("Docstring Coverage by Module")

    for py_file in sorted(python_files):
        result = analyze_file(py_file)
        if result is None:
            continue

        total_functions += result['functions']
        total_functions_with_docs += result['functions_with_docs']
        total_classes += result['classes']
        total_classes_with_docs += result['classes_with_docs']

        total_items = result['functions'] + result['classes']
        items_with_docs = result['functions_with_docs'] + result['classes_with_docs']

        if total_items > 0:
            coverage = (items_with_docs / total_items) * 100
        else:
            coverage = 100

        if result['missing']:
            print(f"{py_file}:")
            print(f"  Coverage: {coverage:.0f}% ({items_with_docs}/{total_items})")
            if result['missing']:
                print("  Missing:")
                MAX_MISSING_TO_SHOW = 5  # Show first N missing items, then summarize rest
                for name, lineno, kind in result['missing'][:MAX_MISSING_TO_SHOW]:
                    print(f"    {name} ({kind}) line {lineno}")
                if len(result['missing']) > MAX_MISSING_TO_SHOW:
                    print(f"    ... {len(result['missing']) - MAX_MISSING_TO_SHOW} more")
            modules_with_gaps.append((py_file, coverage))

    total_items = total_functions + total_classes
    total_documented = total_functions_with_docs + total_classes_with_docs

    if total_items > 0:
        overall_coverage = (total_documented / total_items) * 100
    else:
        overall_coverage = 0

    print(f"Total: {overall_coverage:.0f}% ({total_documented}/{total_items}), {len(python_files)} modules, {len(modules_with_gaps)} need attention")

    sys.exit(0)

if __name__ == '__main__':
    main()
