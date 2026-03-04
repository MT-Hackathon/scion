#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Scan rules for project-specific content before transfer.

Outputs a report of:
- 200+ rules to archive
- Files with ## Project Implementation sections
- Hardcoded project references

Usage:
    python .cursor/skills/rule-authoring-patterns/scripts/scan-project-references.py
"""

import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
RULES_DIR = SCRIPT_DIR.parent.parent


def find_project_specific_rules() -> list[Path]:
    """Find all 200+ rules (project-specific range)."""
    rules = []
    for item in RULES_DIR.iterdir():
        if item.is_dir() and re.match(r"^[2-9]\d{2}-", item.name):
            rules.append(item)
    return sorted(rules, key=lambda p: p.name)


def find_project_implementation_sections() -> list[tuple[Path, int]]:
    """Find files with ## Project Implementation sections."""
    matches = []
    for md_file in RULES_DIR.rglob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        if "## Project Implementation" in content:
            lines = content.split("## Project Implementation")
            if len(lines) > 1:
                section_content = lines[1].split("## ")[0] if "## " in lines[1] else lines[1]
                non_empty = len([ln for ln in section_content.strip().split("\n") 
                               if ln.strip() and not ln.strip().startswith("<!--")])
                matches.append((md_file, non_empty))
    return sorted(matches, key=lambda x: str(x[0]))


def find_hardcoded_references() -> dict[str, list[tuple[Path, int]]]:
    """Find hardcoded project references."""
    patterns = {
        "project_name": re.compile(r"Universal-API", re.IGNORECASE),
        "project_path": re.compile(r"path/to/Universal-API"),
        "backend_path": re.compile(r"src/backend/"),
        "frontend_path": re.compile(r"src/frontend/"),
    }
    
    results: dict[str, list[tuple[Path, int]]] = {k: [] for k in patterns}
    
    for pattern_type in ("*.md", "*.mdc"):
        for file_path in RULES_DIR.rglob(pattern_type):
            if "archived" in str(file_path):
                continue
            content = file_path.read_text(encoding="utf-8")
            for name, pattern in patterns.items():
                matches = pattern.findall(content)
                if matches:
                    results[name].append((file_path, len(matches)))
    
    return results


def main() -> int:
    """Run the scan and output report."""
    print("=" * 60)
    print("RULE TRANSFER SCAN REPORT")
    print("=" * 60)
    print()
    
    project_rules = find_project_specific_rules()
    print(f"## 200+ Rules to Archive: {len(project_rules)}")
    print("-" * 40)
    for rule in project_rules:
        print(f"  {rule.name}/")
    print()
    
    impl_sections = find_project_implementation_sections()
    populated = [(p, c) for p, c in impl_sections if c > 0]
    print(f"## Project Implementation Sections: {len(impl_sections)} total, {len(populated)} with content")
    print("-" * 40)
    for file_path, line_count in impl_sections:
        rel_path = file_path.relative_to(RULES_DIR)
        status = f"({line_count} lines)" if line_count > 0 else "(empty)"
        print(f"  {rel_path} {status}")
    print()
    
    refs = find_hardcoded_references()
    total_refs = sum(len(v) for v in refs.values())
    print(f"## Hardcoded Project References: {total_refs} files")
    print("-" * 40)
    
    for ref_type, matches in refs.items():
        if matches:
            print(f"\n  {ref_type}:")
            for file_path, count in sorted(matches, key=lambda x: str(x[0])):
                rel_path = file_path.relative_to(RULES_DIR)
                print(f"    {rel_path} ({count} occurrences)")
    print()
    
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Rules to archive:           {len(project_rules)}")
    print(f"  Files with impl sections:   {len(impl_sections)}")
    print(f"  Populated impl sections:    {len(populated)}")
    print(f"  Files with hardcoded refs:  {total_refs}")
    print()
    print("Next steps:")
    print("  1. Review this report")
    print("  2. Follow guide-transfer-workflow.md")
    print("  3. Run validate-transfer-ready.py after transfer")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
