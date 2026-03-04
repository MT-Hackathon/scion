#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = ["PyYAML>=6.0"]
# ///
"""
Validate scaffolding file compliance with standards defined in 050-rule-authoring-patterns.

Validates both:
- Rules in .cursor/rules/ (RULE.mdc files with alwaysApply or globs)
- Skills in .cursor/skills/ (SKILL.md files with name field)
"""
import re
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

import yaml


@dataclass
class ValidationIssue:
    file: str
    severity: str  # 'error', 'warning'
    category: str
    message: str
    line: int | None = None

@dataclass
class FileStats:
    file: str
    type: str  # 'rule', 'skill', 'persona'
    tokens: int
    has_frontmatter: bool
    has_anchor: bool
    has_description: bool
    has_references: bool

class ScaffoldingValidator:
    # Token budgets from 050-rule-authoring-patterns
    TOKEN_BUDGETS: ClassVar[dict[str, tuple[int, int]]] = {
        '000-010': (150, 250),  # Always-on universal
        '011-099': (300, 400),  # Universal non-always-on
        '100-199': (350, 550),  # Language-specific
        '200-999': (400, 750),  # Project-specific
    }

    # Valid resource prefixes
    VALID_RESOURCE_PREFIXES: ClassVar[list[str]] = [
        'examples-', 'reference-', 'checklist-', 'guide-', 'cross-references'
    ]
    TOKEN_BUDGET_THRESHOLDS: ClassVar[list[tuple[int, str]]] = [
        (200, '200-999'),
        (100, '100-199'),
        (11, '011-099'),
    ]

    @classmethod
    def get_token_budget(cls, number: int) -> tuple[int, int]:
        """Get token budget based on number range."""
        for threshold, budget_key in cls.TOKEN_BUDGET_THRESHOLDS:
            if number >= threshold:
                return cls.TOKEN_BUDGETS[budget_key]
        return cls.TOKEN_BUDGETS['000-010']

    @classmethod
    def extract_number(cls, folder_name: str) -> int | None:
        """Extract number from folder name like '100-constitution-core'."""
        match = re.match(r'^(\d+)-', folder_name)
        if match:
            return int(match.group(1))
        return None

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.cursor_dir = project_root / ".cursor"
        self.issues: list[ValidationIssue] = []
        self.stats: list[FileStats] = []

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimation: ~4 chars per token"""
        return len(text) // 4

    def extract_frontmatter(self, content: str) -> dict | None:
        """Extract YAML frontmatter if present."""
        lines = content.splitlines()
        if not lines:
            return None

        first = lines[0].lstrip("\ufeff").strip()
        if first != '---':
            return None

        end_idx = None
        for i in range(1, len(lines)):
            if lines[i].strip() == '---':
                end_idx = i
                break

        if end_idx is None:
            return None

        frontmatter_text = "\n".join(lines[1:end_idx])
        if not frontmatter_text.strip():
            return {}

        try:
            return yaml.safe_load(frontmatter_text) or {}
        except yaml.YAMLError:
            return None

    def check_rule_anchor(self, content: str) -> bool:
        """Check if file has proper ANCHORRULE anchor (for RULE files)"""
        return bool(re.search(r'<ANCHORRULE-[\w-]+>', content))

    def check_skill_anchor(self, content: str) -> bool:
        """Check if file has proper ANCHORSKILL anchor (for SKILL files)"""
        return bool(re.search(r'<ANCHORSKILL-[\w-]+>', content))

    def validate_rule_file(self, file_path: Path):
        """Validate a rule file"""
        content = file_path.read_text()
        tokens = self.estimate_tokens(content)
        frontmatter = self.extract_frontmatter(content)
        has_frontmatter = frontmatter is not None
        folder_name = file_path.parent.name

        if not has_frontmatter:
            self.issues.append(ValidationIssue(
                file=str(file_path.relative_to(self.cursor_dir)),
                severity='error',
                category='frontmatter',
                message='Missing YAML frontmatter'
            ))
        else:
            # Rules must have alwaysApply: true OR globs
            has_always = frontmatter.get('alwaysApply') is True
            has_globs = 'globs' in frontmatter and frontmatter.get('globs')

            if not has_always and not has_globs:
                self.issues.append(ValidationIssue(
                    file=str(file_path.relative_to(self.cursor_dir)),
                    severity='error',
                    category='frontmatter',
                    message='Rules must have alwaysApply: true or globs. Migrate to skill.'
                ))

            # Description only required for always-on rules (glob rules selected by pattern)
            if has_always and 'description' not in frontmatter:
                self.issues.append(ValidationIssue(
                    file=str(file_path.relative_to(self.cursor_dir)),
                    severity='error',
                    category='frontmatter',
                    message='Always-on rules need description field'
                ))

        # Check token budget
        number = self.extract_number(folder_name)
        if number is not None:
            min_tokens, max_tokens = self.get_token_budget(number)
            if tokens > max_tokens:
                self.issues.append(ValidationIssue(
                    file=str(file_path.relative_to(self.cursor_dir)),
                    severity='error',
                    category='tokens',
                    message=f'Token count {tokens} exceeds maximum {max_tokens}'
                ))

        # Check resource naming
        resources_dir = file_path.parent / "resources"
        if resources_dir.exists():
            for resource_file in resources_dir.glob("*.md"):
                if not any(resource_file.name.startswith(p) for p in self.VALID_RESOURCE_PREFIXES):
                    self.issues.append(ValidationIssue(
                        file=str(resource_file.relative_to(self.cursor_dir)),
                        severity='warning',
                        category='naming',
                        message='Resource file missing valid prefix'
                    ))

        # Check anchor
        has_anchor = self.check_rule_anchor(content)
        if not has_anchor:
            self.issues.append(ValidationIssue(
                file=str(file_path.relative_to(self.cursor_dir)),
                severity='error',
                category='anchor',
                message='Missing ANCHORRULE anchor'
            ))

        self.stats.append(FileStats(
            file=str(file_path.relative_to(self.cursor_dir)),
            type='rule',
            tokens=tokens,
            has_frontmatter=has_frontmatter,
            has_anchor=has_anchor,
            has_description=frontmatter.get('description') is not None if frontmatter else False,
            has_references='## Reference' in content
        ))

    def validate_skill_file(self, file_path: Path):
        """Validate a skill file"""
        content = file_path.read_text()
        tokens = self.estimate_tokens(content)
        frontmatter = self.extract_frontmatter(content)
        has_frontmatter = frontmatter is not None
        folder_name = file_path.parent.name

        if not has_frontmatter:
            self.issues.append(ValidationIssue(
                file=str(file_path.relative_to(self.cursor_dir)),
                severity='error',
                category='frontmatter',
                message='Missing YAML frontmatter'
            ))
        else:
            # Skills must have name field
            if 'name' not in frontmatter:
                self.issues.append(ValidationIssue(
                    file=str(file_path.relative_to(self.cursor_dir)),
                    severity='error',
                    category='frontmatter',
                    message='Skills must have name field'
                ))

            # Skills should NOT have alwaysApply or globs
            if 'alwaysApply' in frontmatter:
                self.issues.append(ValidationIssue(
                    file=str(file_path.relative_to(self.cursor_dir)),
                    severity='error',
                    category='frontmatter',
                    message='Skills should not have alwaysApply. Migrate to rule.'
                ))

            if 'globs' in frontmatter:
                self.issues.append(ValidationIssue(
                    file=str(file_path.relative_to(self.cursor_dir)),
                    severity='error',
                    category='frontmatter',
                    message='Skills should not have globs. Migrate to rule.'
                ))

            # Check description
            desc = frontmatter.get('description', '')
            if not desc:
                self.issues.append(ValidationIssue(
                    file=str(file_path.relative_to(self.cursor_dir)),
                    severity='error',
                    category='frontmatter',
                    message='Missing description field'
                ))
            else:
                if 'Use when' not in desc:
                    self.issues.append(ValidationIssue(
                        file=str(file_path.relative_to(self.cursor_dir)),
                        severity='warning',
                        category='frontmatter',
                        message='Description missing "Use when" pattern'
                    ))
                if 'DO NOT use' not in desc:
                    self.issues.append(ValidationIssue(
                        file=str(file_path.relative_to(self.cursor_dir)),
                        severity='warning',
                        category='frontmatter',
                        message='Description missing "DO NOT use" pattern'
                    ))

        # Check token budget
        number = self.extract_number(folder_name)
        if number is not None:
            min_tokens, max_tokens = self.get_token_budget(number)
            if tokens > max_tokens:
                self.issues.append(ValidationIssue(
                    file=str(file_path.relative_to(self.cursor_dir)),
                    severity='error',
                    category='tokens',
                    message=f'Token count {tokens} exceeds maximum {max_tokens}'
                ))

        # Check resource naming
        resources_dir = file_path.parent / "resources"
        if resources_dir.exists():
            for resource_file in resources_dir.glob("*.md"):
                if not any(resource_file.name.startswith(p) for p in self.VALID_RESOURCE_PREFIXES):
                    self.issues.append(ValidationIssue(
                        file=str(resource_file.relative_to(self.cursor_dir)),
                        severity='warning',
                        category='naming',
                        message='Resource file missing valid prefix'
                    ))

        # Check anchor
        has_anchor = self.check_skill_anchor(content)
        if not has_anchor:
            self.issues.append(ValidationIssue(
                file=str(file_path.relative_to(self.cursor_dir)),
                severity='error',
                category='anchor',
                message='Missing ANCHORSKILL anchor'
            ))

        self.stats.append(FileStats(
            file=str(file_path.relative_to(self.cursor_dir)),
            type='skill',
            tokens=tokens,
            has_frontmatter=has_frontmatter,
            has_anchor=has_anchor,
            has_description=frontmatter.get('description') is not None if frontmatter else False,
            has_references='## Reference' in content
        ))

    def validate_all(self):
        """Validate all scaffolding files"""
        # Validate rules
        rules_dir = self.cursor_dir / "rules"
        if rules_dir.exists():
            for rule_file in rules_dir.glob("*/RULE.mdc"):
                self.validate_rule_file(rule_file)

        # Validate skills
        skills_dir = self.cursor_dir / "skills"
        if skills_dir.exists():
            for skill_file in skills_dir.glob("*/SKILL.md"):
                self.validate_skill_file(skill_file)

    def print_report(self):
        """Print validation report"""
        print("=" * 80)
        print("SCAFFOLDING FILE COMPLIANCE REPORT")
        print("=" * 80)
        print()

        errors = [i for i in self.issues if i.severity == 'error']
        warnings = [i for i in self.issues if i.severity == 'warning']

        rule_count = len([s for s in self.stats if s.type == 'rule'])
        skill_count = len([s for s in self.stats if s.type == 'skill'])

        print(f"Total files checked: {len(self.stats)}")
        print(f"  Rules:  {rule_count}")
        print(f"  Skills: {skill_count}")
        print()
        print(f"Issues found: {len(self.issues)}")
        print(f"  Errors:   {len(errors)}")
        print(f"  Warnings: {len(warnings)}")
        print()

        if not self.issues:
            print("All scaffolding files are compliant!")
            return

        # Group issues by category
        by_category = {}
        for issue in self.issues:
            if issue.category not in by_category:
                by_category[issue.category] = []
            by_category[issue.category].append(issue)

        for category, issues in sorted(by_category.items()):
            print(f"\n{'=' * 80}")
            print(f"{category.upper()} ISSUES ({len(issues)})")
            print('=' * 80)

            for issue in sorted(issues, key=lambda i: (i.severity != 'error', i.file)):
                icon = "X" if issue.severity == 'error' else "!"
                print(f"\n{icon} {issue.severity.upper()}: {issue.file}")
                print(f"  {issue.message}")


if __name__ == "__main__":
    project_root = Path(__file__).resolve()
    # Walk up to find project root
    while project_root != project_root.parent:
        if (project_root / ".cursor").exists():
            break
        project_root = project_root.parent

    validator = ScaffoldingValidator(project_root)
    validator.validate_all()
    validator.print_report()
