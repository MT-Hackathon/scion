#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Scan scaffolding files for quality issues: missing checklists, examples, decision criteria, etc.
"""
import re
from pathlib import Path


def check_has_checklist(content: str) -> bool:
    """Check if file has a checklist"""
    return '- [ ]' in content or '- [x]' in content or '- [X]' in content

def check_has_code_examples(content: str) -> int:
    """Count code blocks"""
    return content.count('```') // 2

def check_has_decision_criteria(content: str) -> bool:
    """Check if persona has decision criteria section"""
    return 'decision criteria' in content.lower() or 'when to apply' in content.lower()

def check_description_format(content: str) -> tuple[bool, str]:
    """Check YAML frontmatter description format for rules"""
    lines = content.splitlines()
    if not lines or lines[0].strip() != '---':
        return False, "No frontmatter"

    # Find closing ---
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == '---':
            end_idx = i
            break

    if end_idx is None:
        return False, "Malformed frontmatter"

    frontmatter_text = "\n".join(lines[1:end_idx])

    # Check description field
    if 'description:' not in frontmatter_text:
        return False, "No description field"

    # Extract description value (simplified - assumes single or multi-line)
    desc_match = re.search(r'description:\s*["\']?(.+?)(?:["\']?\n|$)', frontmatter_text, re.DOTALL)
    if not desc_match:
        return False, "Cannot parse description"

    description = desc_match.group(1)
    has_use_when = 'use when' in description.lower()
    has_do_not = 'do not use' in description.lower()
    description_status = {
        (True, True): (True, "OK"),
        (True, False): (False, "Missing 'DO NOT use' pattern"),
        (False, True): (False, "Missing 'Use when' pattern"),
        (False, False): (False, "Missing both patterns"),
    }
    return description_status[(has_use_when, has_do_not)]

def check_resource_prefixes(resources_dir: Path) -> list[str]:
    """Check for resource files missing valid prefixes."""
    valid_prefixes = ['examples-', 'reference-', 'checklist-', 'guide-', 'cross-references']
    issues = []
    if resources_dir.exists():
        for resource_file in resources_dir.glob("*.md"):
            if not any(resource_file.name.startswith(prefix) for prefix in valid_prefixes):
                issues.append(resource_file.name)
    return issues


def main():
    project_root = Path(__file__).resolve().parents[4]
    cursor_dir = project_root / ".cursor"

    print("=" * 100)
    print("SCAFFOLDING QUALITY ISSUES SCAN")
    print("=" * 100)

    # Check personas for decision criteria
    print("\n" + "=" * 100)
    print("PERSONAS MISSING DECISION CRITERIA")
    print("=" * 100)

    personas_dir = cursor_dir / "personas"
    personas_missing_criteria = []

    if personas_dir.exists():
        for persona_file in sorted(personas_dir.glob("*.md*")):
            content = persona_file.read_text()
            if not check_has_decision_criteria(content):
                personas_missing_criteria.append(persona_file.name)

    print(f"Total personas missing decision criteria: {len(personas_missing_criteria)}")
    for persona in personas_missing_criteria:
        print(f"  - {persona}")

    # Check rules for description format issues
    print("\n" + "=" * 100)
    print("RULES WITH DESCRIPTION FORMAT ISSUES")
    print("=" * 100)

    rules_dir = cursor_dir / "rules"
    rules_desc_issues = []

    for rule_file in sorted(rules_dir.glob("*/RULE.mdc")):
        content = rule_file.read_text()
        has_correct_format, reason = check_description_format(content)
        if not has_correct_format and reason not in ["No frontmatter", "No description field"]:
            # Only report files that have frontmatter and description but wrong format
            rules_desc_issues.append((rule_file.parent.name, reason))

    print(f"Total rules with description format issues: {len(rules_desc_issues)}")
    for rule, reason in rules_desc_issues:
        print(f"  - {rule}: {reason}")

    # Check resource naming conventions
    print("\n" + "=" * 100)
    print("RESOURCES WITH INVALID PREFIXES")
    print("=" * 100)

    resources_issues = []
    for rule_dir in sorted(rules_dir.glob("*")):
        if rule_dir.is_dir():
            resources_dir = rule_dir / "resources"
            bad_files = check_resource_prefixes(resources_dir)
            for bad_file in bad_files:
                resources_issues.append((rule_dir.name, bad_file))

    print(f"Total resources with invalid prefixes: {len(resources_issues)}")
    for rule, resource in resources_issues:
        print(f"  - {rule}/resources/{resource}")

    # Summary
    print("\n" + "=" * 100)
    print("QUALITY ISSUES SUMMARY")
    print("=" * 100)
    print(f"Personas missing decision criteria: {len(personas_missing_criteria)}")
    print(f"Rules with description issues: {len(rules_desc_issues)}")
    print(f"Resources with invalid prefixes: {len(resources_issues)}")
    print(f"\nTotal quality issues: {len(personas_missing_criteria) + len(rules_desc_issues) + len(resources_issues)}")

if __name__ == "__main__":
    main()
