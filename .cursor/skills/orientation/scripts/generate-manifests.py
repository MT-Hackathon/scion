#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = ["pyyaml>=6.0"]
# ///
"""Generate skills-manifest.md and rules-manifest.md from .cursor/ frontmatter.

Reads YAML frontmatter from all .cursor/skills/*/SKILL.md and
.cursor/rules/*/RULE.mdc, then writes manifest files that point to
.claude/ paths (the cross-IDE replicated copy).

Usage:
    uv run generate-manifests.py <cursor_dir> [--output-dir <dir>]
    uv run generate-manifests.py .cursor --output-dir .aiassistant/rules
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml


def _parse_frontmatter(filepath: Path) -> dict:
    """Extract YAML frontmatter from a file delimited by --- lines."""
    text = filepath.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    end = text.index("---", 3)
    return yaml.safe_load(text[3:end]) or {}


def _extract_first_heading(filepath: Path) -> str | None:
    """Extract the first markdown heading from a file, skipping frontmatter."""
    text = filepath.read_text(encoding="utf-8")
    lines = text.split("\n")
    in_frontmatter = False
    for line in lines:
        if line.strip() == "---":
            in_frontmatter = not in_frontmatter
            continue
        if in_frontmatter:
            continue
        if line.startswith("#"):
            return line.lstrip("#").strip()
    return None


def _humanize(name: str) -> str:
    """Convert a kebab-case directory name to a readable description."""
    return name.replace("-", " ").replace("_", " ").title()


def _collect_skills(cursor_dir: Path) -> list[dict]:
    """Collect skill metadata from all SKILL.md files."""
    skills_dir = cursor_dir / "skills"
    if not skills_dir.is_dir():
        return []
    entries = []
    for skill_dir in sorted(skills_dir.iterdir()):
        skill_file = skill_dir / "SKILL.md"
        if not skill_dir.is_dir() or not skill_file.exists():
            continue
        fm = _parse_frontmatter(skill_file)
        name = fm.get("name", skill_dir.name)
        description = fm.get("description", "").strip()
        if not description:
            description = _extract_first_heading(skill_file) or _humanize(skill_dir.name)
        entries.append({"name": name, "dir_name": skill_dir.name, "description": description})
    return entries


def _collect_rules(cursor_dir: Path) -> list[dict]:
    """Collect rule metadata from all RULE.mdc files and resource directories."""
    rules_dir = cursor_dir / "rules"
    if not rules_dir.is_dir():
        return []
    entries = []
    for rule_dir in sorted(rules_dir.iterdir()):
        if not rule_dir.is_dir():
            continue
        rule_file = rule_dir / "RULE.mdc"
        if rule_file.exists():
            fm = _parse_frontmatter(rule_file)
            description = fm.get("description", "").strip()
            always_apply = fm.get("alwaysApply", False)
            if not description:
                description = _extract_first_heading(rule_file) or _humanize(rule_dir.name)
            entries.append({
                "name": rule_dir.name,
                "description": description,
                "always_apply": always_apply,
                "has_rule_file": True,
            })
        else:
            md_files = list(rule_dir.rglob("*.md"))
            if md_files:
                description = _humanize(rule_dir.name)
                entries.append({
                    "name": rule_dir.name,
                    "description": description,
                    "always_apply": False,
                    "has_rule_file": False,
                })
    return entries


def _render_skills_manifest(skills: list[dict]) -> str:
    """Render the skills manifest markdown."""
    lines = [
        "# Skills Manifest",
        "",
        "Extended skills with resources and scripts. Each skill is a manifest of its own folder contents.",
        "Read the skill file when the description matches your current task.",
    ]
    for skill in skills:
        lines.extend([
            "",
            f"## {skill['dir_name']}",
            f"**Path**: `.claude/skills/{skill['dir_name']}/SKILL.md`",
            skill["description"],
        ])
    lines.append("")
    return "\n".join(lines)


def _render_rules_manifest(rules: list[dict]) -> str:
    """Render the rules manifest markdown."""
    always_on = [r for r in rules if r["always_apply"]]
    additional = [r for r in rules if not r["always_apply"]]

    lines = [
        "# Rules Manifest",
        "",
        "Extended rules for coding standards. Read the file when the description matches your current task.",
        "",
        "## Always Applied",
        "",
        "These rules are always active (content is in ProjectRules.md).",
    ]
    for rule in always_on:
        path_suffix = "RULE.mdc" if rule.get("has_rule_file", True) else ""
        path = f".claude/rules/{rule['name']}/{path_suffix}".rstrip("/")
        lines.extend(["", f"### {rule['name']}", f"**Path**: `{path}`", rule["description"]])

    lines.extend(["", "## Additional Rules", "", "Read these when the description matches your current task."])
    for rule in additional:
        path_suffix = "RULE.mdc" if rule.get("has_rule_file", True) else ""
        path = f".claude/rules/{rule['name']}/{path_suffix}".rstrip("/")
        lines.extend(["", f"### {rule['name']}", f"**Path**: `{path}`", rule["description"]])
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate AI assistant manifests from .cursor frontmatter")
    parser.add_argument("cursor_dir", type=Path, help="Path to .cursor directory")
    parser.add_argument("--output-dir", type=Path, default=None, help="Output directory (default: sibling .aiassistant/rules/)")
    args = parser.parse_args()

    cursor_dir = args.cursor_dir.resolve()
    if not cursor_dir.is_dir():
        print(f"Error: {cursor_dir} is not a directory", file=sys.stderr)
        return 1

    output_dir = args.output_dir
    if output_dir is None:
        output_dir = cursor_dir.parent / ".aiassistant" / "rules"
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    skills = _collect_skills(cursor_dir)
    rules = _collect_rules(cursor_dir)

    skills_path = output_dir / "skills-manifest.md"
    rules_path = output_dir / "rules-manifest.md"

    skills_path.write_text(_render_skills_manifest(skills), encoding="utf-8")
    rules_path.write_text(_render_rules_manifest(rules), encoding="utf-8")

    print(f"Generated {skills_path} ({len(skills)} skills)")
    print(f"Generated {rules_path} ({len(rules)} rules)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
