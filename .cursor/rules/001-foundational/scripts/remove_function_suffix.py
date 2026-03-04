#!/usr/bin/env python3
"""
Batch rename script to remove _function suffix from Python functions.
Preserves _system suffix for ECS system functions.
"""

import ast
import re
import sys
from pathlib import Path


def find_function_definitions(content: str) -> list[tuple[str, str]]:
    """
    Find all function definitions with _function suffix.
    Returns list of (old_name, new_name) tuples.
    """
    pattern = r'def\s+(\w+_function)\s*\('
    matches = re.finditer(pattern, content)

    renames = []
    for match in matches:
        old_name = match.group(1)
        # Skip if it contains _system (shouldn't happen, but be safe)
        if '_system' in old_name:
            continue
        # Remove _function suffix
        FUNCTION_SUFFIX = "_function"
        FUNCTION_SUFFIX_LEN = len(FUNCTION_SUFFIX)
        if old_name.endswith(FUNCTION_SUFFIX):
            new_name = old_name[:-FUNCTION_SUFFIX_LEN]
            renames.append((old_name, new_name))

    return renames


def replace_function_names(content: str, renames: list[tuple[str, str]]) -> str:
    """
    Replace all occurrences of old function names with new names.
    Uses word boundaries to avoid partial matches.
    """
    modified_content = content

    for old_name, new_name in renames:
        # Match function name with word boundaries
        # This catches: function_name( or function_name) or function_name, etc.
        pattern = r'\b' + re.escape(old_name) + r'\b'
        modified_content = re.sub(pattern, new_name, modified_content)

    return modified_content


def validate_syntax(file_path: Path, content: str) -> bool:
    """
    Validate Python syntax using AST parsing.
    """
    try:
        ast.parse(content)
        return True
    except SyntaxError as e:
        print(f"❌ Syntax error in {file_path}: {e}")
        return False


def process_file(file_path: Path) -> tuple[int, int]:
    """
    Process a single Python file to remove _function suffixes.
    Returns (definitions_changed, total_replacements).
    """
    try:
        with open(file_path, encoding='utf-8') as f:
            original_content = f.read()
    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}")
        return 0, 0

    # Find all function definitions to rename
    renames = find_function_definitions(original_content)

    if not renames:
        return 0, 0

    # Apply replacements
    modified_content = replace_function_names(original_content, renames)

    # Validate syntax
    if not validate_syntax(file_path, modified_content):
        print(f"⚠️  Skipping {file_path} due to syntax error")
        return 0, 0

    # Count total replacements
    total_replacements = 0
    for old_name, _new_name in renames:
        total_replacements += original_content.count(old_name)

    # Write back
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(modified_content)
    except Exception as e:
        print(f"❌ Error writing {file_path}: {e}")
        return 0, 0

    print(f"✓ {file_path}: {len(renames)} definitions, {total_replacements} total replacements")
    for old_name, new_name in renames:
        print(f"  - {old_name} → {new_name}")

    return len(renames), total_replacements


def main():
    """
    Main entry point for batch refactoring script.
    """
    # Get project root
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent.parent.parent

    # Find all Python files with _function suffix
    print("🔍 Searching for Python files with _function suffix...")
    print()

    # Process in order: src/backend → tests → simulation → examples
    search_dirs = [
        project_root / "src" / "backend",
        project_root / "tests",
        project_root / "simulation",
        project_root / "examples",
        project_root / "src",  # For src/main.py
    ]

    total_files = 0
    total_definitions = 0
    total_replacements = 0

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue

        # Find all .py files in this directory
        py_files = sorted(search_dir.rglob("*.py"))

        for py_file in py_files:
            defs, reps = process_file(py_file)
            if defs > 0:
                total_files += 1
                total_definitions += defs
                total_replacements += reps

    print()
    print("=" * 60)
    print("✅ Complete!")
    print(f"   Files modified: {total_files}")
    print(f"   Function definitions renamed: {total_definitions}")
    print(f"   Total replacements: {total_replacements}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())

