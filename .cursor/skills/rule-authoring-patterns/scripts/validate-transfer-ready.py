#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Validate that rules are ready for transfer to a new project.

Checks:
- No 200+ rules remain in .cursor/rules/
- No populated ## Project Implementation sections
- Project Information has placeholders (not project-specific values)

Usage:
    python .cursor/skills/rule-authoring-patterns/scripts/validate-transfer-ready.py
"""

import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
RULES_DIR = SCRIPT_DIR.parent.parent

# Patterns that indicate project-specific content (should be replaced with placeholders)
PROJECT_SPECIFIC_PATTERNS = [
    re.compile(r"Universal-API", re.IGNORECASE),
    re.compile(r"path/to/Universal-API"),
]

# Expected placeholder patterns
PLACEHOLDER_PATTERN = re.compile(r"\{\{[A-Z_]+\}\}")


def check_no_project_rules() -> tuple[bool, list[str]]:
    """Check that no 200+ rules exist."""
    issues = []
    for item in RULES_DIR.iterdir():
        if item.is_dir() and re.match(r"^[2-9]\d{2}-", item.name):
            issues.append(f"Project-specific rule still exists: {item.name}/")
    return len(issues) == 0, issues


def check_implementation_sections_cleared() -> tuple[bool, list[str]]:
    """Check that ## Project Implementation sections are empty or have placeholders."""
    issues = []
    for md_file in RULES_DIR.rglob("*.md"):
        # Skip transfer documentation itself
        if "guide-transfer" in md_file.name or "reference-project-markers" in md_file.name:
            continue
            
        content = md_file.read_text(encoding="utf-8")
        if "## Project Implementation" in content:
            parts = content.split("## Project Implementation")
            if len(parts) > 1:
                section = parts[1].split("## ")[0] if "## " in parts[1] else parts[1]
                # Filter out empty lines and HTML comments
                content_lines = [
                    ln for ln in section.strip().split("\n")
                    if ln.strip() and not ln.strip().startswith("<!--")
                ]
                if content_lines:
                    rel_path = md_file.relative_to(RULES_DIR)
                    issues.append(f"Populated section in: {rel_path}")
    return len(issues) == 0, issues


def check_project_info_has_placeholders() -> tuple[bool, list[str]]:
    """Check that 001-foundational has placeholders, not project values."""
    issues = []
    foundational = RULES_DIR / "001-foundational" / "RULE.mdc"
    
    if not foundational.exists():
        issues.append("001-foundational/RULE.mdc not found")
        return False, issues
    
    content = foundational.read_text(encoding="utf-8")
    
    # Extract Project Information section
    if "### Project Information" not in content:
        issues.append("Project Information section not found in 001-foundational")
        return False, issues
    
    section_start = content.find("### Project Information")
    section_end = content.find("###", section_start + 1)
    if section_end == -1:
        section_end = len(content)
    
    project_section = content[section_start:section_end]
    
    # Check for project-specific values
    for pattern in PROJECT_SPECIFIC_PATTERNS:
        if pattern.search(project_section):
            issues.append(f"Project-specific value found: {pattern.pattern}")
    
    # Check for expected placeholders
    if not PLACEHOLDER_PATTERN.search(project_section):
        issues.append("No placeholders found in Project Information section")
    
    return len(issues) == 0, issues


def check_no_hardcoded_references() -> tuple[bool, list[str]]:
    """Check for remaining hardcoded project references in 000-199 rules."""
    issues = []
    
    for pattern_type in ("*.md", "*.mdc"):
        for file_path in RULES_DIR.rglob(pattern_type):
            # Skip 200+ rules (should be archived), transfer docs, and this script
            if re.match(r"^[2-9]\d{2}-", file_path.parent.name):
                continue
            if "guide-transfer" in file_path.name or "reference-project-markers" in file_path.name:
                continue
            
            content = file_path.read_text(encoding="utf-8")
            
            for pattern in PROJECT_SPECIFIC_PATTERNS:
                if pattern.search(content):
                    rel_path = file_path.relative_to(RULES_DIR)
                    issues.append(f"Hardcoded reference in: {rel_path} ({pattern.pattern})")
                    break  # Only report once per file
    
    return len(issues) == 0, issues


def main() -> int:
    """Run all validation checks."""
    print("=" * 60)
    print("TRANSFER READINESS VALIDATION")
    print("=" * 60)
    print()
    
    all_passed = True
    
    checks = [
        ("No 200+ rules remain", check_no_project_rules),
        ("Implementation sections cleared", check_implementation_sections_cleared),
        ("Project Info has placeholders", check_project_info_has_placeholders),
        ("No hardcoded references", check_no_hardcoded_references),
    ]
    
    for name, check_fn in checks:
        passed, issues = check_fn()
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {name}")
        
        if not passed:
            all_passed = False
            for issue in issues:
                print(f"       - {issue}")
        print()
    
    print("=" * 60)
    if all_passed:
        print("RESULT: Rules are ready for transfer")
        print()
        print("Next steps:")
        print("  1. Copy .cursor/rules/ to new project")
        print("  2. Replace placeholders with new project values")
        print("  3. Create 200+ rules as project patterns emerge")
        return 0
    else:
        print("RESULT: Issues found - address before transfer")
        print()
        print("See guide-transfer-workflow.md for remediation steps")
        return 1


if __name__ == "__main__":
    sys.exit(main())
