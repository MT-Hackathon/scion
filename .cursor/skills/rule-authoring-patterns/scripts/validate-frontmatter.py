#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = ["PyYAML>=6.0"]
# ///
"""
Validate scaffolding rule and skill frontmatter descriptions.

Checks for:
- Truncated descriptions (ending with `...`)
- Missing "Use when/DO NOT use" patterns in intelligent skills
- Missing required frontmatter fields (name for skills, alwaysApply/globs for rules)

Usage:
    python validate-frontmatter.py

Exit codes:
    0: All validations passed
    1: Validation errors found
    2: Script error
"""

import re
import sys
from pathlib import Path

import yaml


def find_cursor_dir() -> Path:
    """Find the .cursor directory by walking up from script location."""
    script_dir = Path(__file__).resolve().parent
    current = script_dir
    while current != current.parent:
        cursor_dir = current / ".cursor"
        if cursor_dir.exists():
            return cursor_dir
        current = current.parent
    return script_dir.parent.parent.parent


def parse_file(path: Path) -> tuple[dict, str]:
    """Parse YAML frontmatter and body from rule/skill file."""
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return {}, content

    end_match = re.search(r"^---$", content[3:], re.MULTILINE)
    if not end_match:
        return {}, content

    fm_end = end_match.start() + 3 + 3
    frontmatter_text = content[4:end_match.start() + 3]
    body = content[fm_end:]

    try:
        frontmatter = yaml.safe_load(frontmatter_text) or {}
    except yaml.YAMLError as e:
        return {"_parse_error": str(e)}, body

    return frontmatter, body


def validate_rules(rules_dir: Path) -> tuple[list[str], list[str]]:
    """Validate all rule files in .cursor/rules/."""
    errors, warnings = [], []
    if not rules_dir.exists():
        return errors, warnings

    for rule_file in sorted(rules_dir.glob("*/RULE.mdc")):
        frontmatter, _ = parse_file(rule_file)
        name = rule_file.parent.name

        if "_parse_error" in frontmatter:
            errors.append(f"[RULE] {name}: YAML parse error: {frontmatter['_parse_error']}")
            continue

        has_always = frontmatter.get("alwaysApply") is True
        has_globs = "globs" in frontmatter and frontmatter.get("globs")

        if not has_always and not has_globs:
            errors.append(f"[RULE] {name}: Rules must have 'alwaysApply: true' or 'globs'")

        # Description only required for always-on rules (glob rules are selected by pattern, not description)
        if has_always and "description" not in frontmatter:
            errors.append(f"[RULE] {name}: Always-on rules need 'description'")

        desc = frontmatter.get("description", "")
        if desc and desc.endswith("..."):
            errors.append(f"[RULE] {name}: Description truncated")

    return errors, warnings


def validate_skills(skills_dir: Path) -> tuple[list[str], list[str]]:
    """Validate all skill files in .cursor/skills/."""
    errors, warnings = [], []
    if not skills_dir.exists():
        return errors, warnings

    for skill_file in sorted(skills_dir.glob("*/SKILL.md")):
        frontmatter, _ = parse_file(skill_file)
        name = skill_file.parent.name

        if "_parse_error" in frontmatter:
            errors.append(f"[SKILL] {name}: YAML parse error: {frontmatter['_parse_error']}")
            continue

        if "name" not in frontmatter:
            errors.append(f"[SKILL] {name}: Missing 'name'")

        if "alwaysApply" in frontmatter:
            errors.append(f"[SKILL] {name}: Skills should not have 'alwaysApply'")

        if "globs" in frontmatter:
            errors.append(f"[SKILL] {name}: Skills should not have 'globs'")

        if "description" not in frontmatter:
            errors.append(f"[SKILL] {name}: Missing 'description'")
            continue

        desc = frontmatter.get("description", "")
        if desc.endswith("..."):
            errors.append(f"[SKILL] {name}: Description truncated")

        if "Use when" not in desc:
            warnings.append(f"[SKILL] {name}: Missing 'Use when' pattern")
        if "DO NOT use" not in desc:
            warnings.append(f"[SKILL] {name}: Missing 'DO NOT use' pattern")

    return errors, warnings


def main():
    """Main entry point."""
    try:
        cursor_dir = find_cursor_dir()
        print(f"Validating in: {cursor_dir}\n")

        r_err, r_warn = validate_rules(cursor_dir / "rules")
        s_err, s_warn = validate_skills(cursor_dir / "skills")

        errors = r_err + s_err
        warnings = r_warn + s_warn

        if errors:
            print("ERRORS:")
            for e in errors:
                print(f"  ✗ {e}")
        if warnings:
            print("WARNINGS:")
            for w in warnings:
                print(f"  ⚠ {w}")
        if not errors and not warnings:
            print("✓ All validations passed")

        sys.exit(1 if errors else 0)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
