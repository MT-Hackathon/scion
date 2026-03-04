#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
generate-new-rule.py - Interactive rule/skill/agent scaffolding using 050's patterns.

This script creates the structure for a new rule, skill, or agent:

Rules:
- Folder with correct naming ({number}-{name}/)
- RULE.mdc with proper frontmatter, anchor, and TOC skeleton
- resources/ and scripts/ folders
- Location: .cursor/rules/

Skills:
- Folder with correct naming ({number}-{name}/)
- SKILL.md with proper frontmatter, anchor, and TOC skeleton
- resources/ and scripts/ folders
- Location: .cursor/skills/

Agents:
- Single file ({name}.md) with frontmatter and system prompt
- No subdirectories (simpler than rules/skills)
- Location: .cursor/agents/

The script provides STRUCTURE, not CONTENT. You fill in the domain expertise.

Usage:
    python generate-new-rule.py
    python generate-new-rule.py --type skill --number 275 --name api-versioning --category code
    python generate-new-rule.py --type rule --number 150 --name rust-patterns --globs "*.rs"
    python generate-new-rule.py --type agent --name code-reviewer --model inherit
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import NamedTuple


class RuleCategory(NamedTuple):
    """Category definition with associated resource suggestions."""

    name: str
    number_ranges: list[tuple[int, int]]
    token_budget: str
    required_resources: list[str]
    optional_resources: list[str]
    description: str


# Category definitions based on 050's patterns
CATEGORIES: dict[str, RuleCategory] = {
    "meta": RuleCategory(
        name="Meta/Framework",
        number_ranges=[(0, 99)],
        token_budget="300-400t",
        required_resources=["reference-{topic}.md", "checklist-{topic}.md"],
        optional_resources=["examples-{topic}.md"],
        description="Environment, paths, tooling, rule governance",
    ),
    "code": RuleCategory(
        name="Code Architecture",
        number_ranges=[(100, 199)],
        token_budget="350-550t",
        required_resources=["examples-{topic}.md", "reference-{topic}.md"],
        optional_resources=["checklist-{topic}.md"],
        description="Code standards, invariants, architecture patterns",
    ),
    "packages": RuleCategory(
        name="Packages/Dependencies",
        number_ranges=[(200, 209)],
        token_budget="400-750t",
        required_resources=["reference-{topic}.md"],
        optional_resources=["examples-{topic}.md"],
        description="Package selection, dependency management",
    ),
    "ui": RuleCategory(
        name="UI/Visual",
        number_ranges=[(210, 250)],
        token_budget="400-750t",
        required_resources=["examples-{topic}.md", "reference-{topic}.md"],
        optional_resources=["checklist-{topic}.md", "guide-{topic}.md"],
        description="Frontend patterns, styling, components, visual design",
    ),
    "workflow": RuleCategory(
        name="Workflow/Process",
        number_ranges=[(251, 299)],
        token_budget="400-750t",
        required_resources=["guide-{topic}.md", "checklist-{topic}.md"],
        optional_resources=["examples-{topic}.md", "reference-{topic}.md"],
        description="Integration, testing, error handling, processes",
    ),
}


def detect_category_from_number(number: int) -> str | None:
    """Detect rule category based on number range."""
    for cat_key, category in CATEGORIES.items():
        for start, end in category.number_ranges:
            if start <= number <= end:
                return cat_key
    return None


def get_token_budget(number: int) -> str:
    """Get token budget based on rule number."""
    thresholds = [
        (200, "400-750t"),
        (100, "350-550t"),
        (11, "300-400t"),
    ]
    for threshold, budget in thresholds:
        if number >= threshold:
            return budget
    return "150-250t (always-on, must be lean)"


def prompt_user(prompt: str, default: str = "") -> str:
    """Prompt user for input with optional default."""
    if default:
        user_input = input(f"{prompt} [{default}]: ").strip()
        return user_input if user_input else default
    return input(f"{prompt}: ").strip()


def prompt_choice(prompt: str, options: list[str]) -> str:
    """Prompt user to choose from options."""
    print(f"\n{prompt}")
    for i, opt in enumerate(options, 1):
        print(f"  [{i}] {opt}")
    while True:
        choice = input("Choice: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return options[int(choice) - 1]
        print(f"Please enter a number 1-{len(options)}")


def prompt_multi_choice(prompt: str, options: list[str]) -> list[str]:
    """Prompt user to choose multiple options."""
    print(f"\n{prompt}")
    for i, opt in enumerate(options, 1):
        print(f"  [{i}] {opt}")
    print("  [a] All")
    print("  [n] None")

    while True:
        choice = input("Choice (comma-separated, or 'a' for all, 'n' for none): ").strip().lower()
        if choice == "a":
            return options
        if choice == "n":
            return []
        try:
            indices = [int(x.strip()) for x in choice.split(",")]
            if all(1 <= i <= len(options) for i in indices):
                return [options[i - 1] for i in indices]
        except ValueError:
            pass
        print(f"Please enter numbers 1-{len(options)} separated by commas, or 'a'/'n'")


def find_cursor_dir() -> Path:
    """Find the .cursor directory by walking up from script location."""
    script_dir = Path(__file__).parent.resolve()
    current = script_dir
    while current != current.parent:
        cursor_dir = current / ".cursor"
        if cursor_dir.exists():
            return cursor_dir
        current = current.parent
    # Fallback: assume we're in .cursor/skills/.../scripts/
    return script_dir.parent.parent.parent


def generate_skill_structure(
    skills_dir: Path,
    number: int,
    name: str,
    category_key: str,
    selected_resources: list[str],
) -> None:
    """Generate the skill folder structure."""
    folder_name = f"{number:03d}-{name}"
    skill_path = skills_dir / folder_name

    if skill_path.exists():
        print(f"\nError: Skill folder already exists: {skill_path}")
        sys.exit(1)

    # Create directories
    skill_path.mkdir(parents=True)
    (skill_path / "resources").mkdir()
    (skill_path / "scripts").mkdir()

    # Generate anchor name from rule name
    anchor_name = name.upper().replace("-", "-")

    # Get category info
    category = CATEGORIES.get(category_key)

    # Generate resource list for manifest
    resource_entries = []
    for res in selected_resources:
        prefix = res.split("-")[0]
        purpose_map = {
            "examples": "Working patterns and code samples",
            "reference": "Lookup data and specifications",
            "checklist": "Validation gates and requirements",
            "guide": "Step-by-step procedures",
        }
        purpose = purpose_map.get(prefix, "Documentation")
        resource_entries.append(f"- **{res}** - When: [FILL]; What: {purpose}")

    resources_section = "\n".join(resource_entries) if resource_entries else "- [No resources yet]"

    # Generate SKILL.md content (no alwaysApply, has name field)
    skill_content = f'''---
name: {folder_name}
description: "[FILL: Use when X. DO NOT use for Y. Be specific to procurement-web.]"
---

<ANCHORSKILL-{anchor_name}>

# {name.replace("-", " ").title()}

## What This Skill Provides

### Resources
{resources_section}

### Scripts
- [No scripts yet]

## Core Concepts

[FILL: Your specific patterns here. Remember the Specificity Principle - encode how procurement-web does this, not generic best practices.]

### [Topic 1]

[FILL]

### [Topic 2]

[FILL]

## Cross-References

**Related skills/rules:**
- [FILL: Link to related skills/rules]

**Defined anchors:**
- `ANCHORSKILL-{anchor_name}`: [FILL: Brief description]

</ANCHORSKILL-{anchor_name}>
'''

    # Write SKILL.md
    (skill_path / "SKILL.md").write_text(skill_content)

    # Create placeholder resource files
    for res in selected_resources:
        prefix = res.split("-")[0]
        resource_content = f'''# {prefix.title()}: {name.replace("-", " ").title()}

[FILL: Add content here]

---

## [Section 1]

[FILL]

## [Section 2]

[FILL]
'''
        (skill_path / "resources" / res).write_text(resource_content)

    # Create .gitkeep in scripts if empty
    (skill_path / "scripts" / ".gitkeep").write_text("")

    print(f"\n{'=' * 60}")
    print(f"Created skill: {folder_name}")
    print(f"{'=' * 60}")


# Available models for agents
AGENT_MODELS: dict[str, str] = {
    "inherit": "Use parent agent's model (default)",
    "fast": "Quick, less capable model",
    "gpt-5.3-codex": "Implementation, QA, visual audit",
    "gpt-5.3-codex-high": "Architecture, plan verification, deep reasoning",
    "gemini-3-flash": "Fast documentation generation",
    "claude-opus-4-5-20251101": "Complex reasoning, architecture",
}


def generate_agent_structure(
    agents_dir: Path,
    name: str,
    model: str,
    readonly: bool = False,
    is_background: bool = False,
) -> None:
    """Generate the agent file structure (single file, no subdirectories)."""
    agent_file = agents_dir / f"{name}.md"

    if agent_file.exists():
        print(f"\nError: Agent file already exists: {agent_file}")
        sys.exit(1)

    # Ensure agents directory exists
    agents_dir.mkdir(parents=True, exist_ok=True)

    # Build frontmatter
    frontmatter_lines = [
        "---",
        f"name: {name}",
        "description: |",
        "  [FILL: When to use this agent. Include trigger phrases.",
        "  Describe what it does and what it does NOT do.",
        "  Add 'Use proactively' if it should auto-delegate.]",
        f"model: {model}",
    ]
    if readonly:
        frontmatter_lines.append("readonly: true")
    if is_background:
        frontmatter_lines.append("is_background: true")
    frontmatter_lines.append("---")

    frontmatter = "\n".join(frontmatter_lines)

    # Generate agent content
    title = name.replace("-", " ").title()
    agent_content = f"""{frontmatter}

# {title}

[FILL: One sentence defining your role and purpose.]

## Workflow

1. **Receive**: [FILL: What input does this agent expect?]
2. **Analyze**: [FILL: How does it process the input?]
3. **Execute**: [FILL: What actions does it take?]
4. **Return**: [FILL: What output format does it produce?]

## Output Format

[FILL: Specify expected output structure. Use JSON for structured agents:]

```json
{{
  "example_field": "value",
  "issues": []
}}
```

## Constraints

- [FILL: What should this agent NOT do?]
- [FILL: Hard limits on scope]
- [FILL: Quality gates before returning]

## Examples

### Example Input

```
[FILL: Sample input]
```

### Example Output

```
[FILL: Sample output]
```
"""

    # Write agent file
    agent_file.write_text(agent_content)

    print(f"\n{'=' * 60}")
    print(f"Created agent: {name}.md")
    print(f"{'=' * 60}")
    print(f"\nFile: {agent_file}")
    print(f"Model: {model} ({AGENT_MODELS.get(model, 'Custom')})")
    if readonly:
        print("Mode: Read-only")
    if is_background:
        print("Execution: Background (non-blocking)")
    print(f"\nNext steps:")
    print(f"  1. Edit {name}.md - fill in description (critical for delegation)")
    print(f"  2. Complete the system prompt sections")
    print(f"  3. Test with explicit invocation: /{name} [task]")
    print(f"  4. Test automatic delegation by describing matching tasks")


def generate_rule_structure(
    rules_dir: Path,
    number: int,
    name: str,
    category_key: str,
    selected_resources: list[str],
    globs: str | None = None,
    always_apply: bool = False,
) -> None:
    """Generate the rule folder structure."""
    folder_name = f"{number:03d}-{name}"
    rule_path = rules_dir / folder_name

    if rule_path.exists():
        print(f"\nError: Rule folder already exists: {rule_path}")
        sys.exit(1)

    # Create directories
    rule_path.mkdir(parents=True)
    (rule_path / "resources").mkdir()
    (rule_path / "scripts").mkdir()

    # Generate anchor name from rule name
    anchor_name = name.upper().replace("-", "-")

    # Get category info
    category = CATEGORIES.get(category_key)

    # Generate resource list for manifest
    resource_entries = []
    for res in selected_resources:
        prefix = res.split("-")[0]
        purpose_map = {
            "examples": "Working patterns and code samples",
            "reference": "Lookup data and specifications",
            "checklist": "Validation gates and requirements",
            "guide": "Step-by-step procedures",
        }
        purpose = purpose_map.get(prefix, "Documentation")
        resource_entries.append(f"- **{res}** - When: [FILL]; What: {purpose}")

    resources_section = "\n".join(resource_entries) if resource_entries else "- [No resources yet]"

    # Build frontmatter based on activation type
    if always_apply:
        frontmatter = '''---
description: "[FILL: Use when X. DO NOT use for Y. Be specific to procurement-web.]"
alwaysApply: true
---'''
    elif globs:
        frontmatter = f'''---
description: "[FILL: Use when X. DO NOT use for Y. Be specific to procurement-web.]"
globs: "{globs}"
---'''
    else:
        # This shouldn't happen for rules - should be a skill instead
        print("Warning: Rules should have alwaysApply: true or globs. Use --type skill instead.")
        frontmatter = '''---
description: "[FILL: Use when X. DO NOT use for Y. Be specific to procurement-web.]"
alwaysApply: true
---'''

    # Generate RULE.mdc content
    rule_content = f'''{frontmatter}

<ANCHORRULE-{anchor_name}>

# {name.replace("-", " ").title()}

## What This Rule Provides

### Resources
{resources_section}

### Scripts
- [No scripts yet]

## Core Concepts

[FILL: Your specific patterns here. Remember the Specificity Principle - encode how procurement-web does this, not generic best practices.]

### [Topic 1]

[FILL]

### [Topic 2]

[FILL]

## Cross-References

**Related rules:**
- [FILL: Link to related rules]

**Defined anchors:**
- `ANCHORRULE-{anchor_name}`: [FILL: Brief description]

</ANCHORRULE-{anchor_name}>
'''

    # Write RULE.mdc
    (rule_path / "RULE.mdc").write_text(rule_content)

    # Create placeholder resource files
    for res in selected_resources:
        prefix = res.split("-")[0]
        resource_content = f'''# {prefix.title()}: {name.replace("-", " ").title()}

[FILL: Add content here]

---

## [Section 1]

[FILL]

## [Section 2]

[FILL]
'''
        (rule_path / "resources" / res).write_text(resource_content)

    # Create .gitkeep in scripts if empty
    (rule_path / "scripts" / ".gitkeep").write_text("")

    print(f"\n{'=' * 60}")
    print(f"Created rule: {folder_name}")
    print(f"{'=' * 60}")
    print(f"\nStructure:")
    print(f"  {folder_name}/")
    print(f"  ├── RULE.mdc")
    print(f"  ├── resources/")
    for res in selected_resources:
        print(f"  │   └── {res}")
    print(f"  └── scripts/")
    print(f"\nToken budget: {get_token_budget(number)}")
    print(f"Category: {category.name if category else 'Project-specific'}")
    if globs:
        print(f"Activation: Glob-based ({globs})")
    else:
        print("Activation: Always-on")
    print(f"\nNext steps:")
    print(f"  1. Edit RULE.mdc - fill in description, core concepts")
    print(f"  2. Edit resource files - add your specific patterns")
    print(f"  3. Run validate-frontmatter.py to check metadata")
    print(f"  4. Run validate-scaffolding-compliance.py to check structure")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate a new rule, skill, or agent using 050's patterns",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate-new-rule.py
  python generate-new-rule.py --type skill --number 275 --name api-versioning --category code
  python generate-new-rule.py --type rule --number 150 --name rust-patterns --globs "*.rs"
  python generate-new-rule.py --type agent --name code-reviewer --model gpt-5.3-codex
        """,
    )
    parser.add_argument("--type", type=str, choices=["rule", "skill", "agent"], 
                        help="Type: 'rule' for always-on/glob-based, 'skill' for intelligent activation, 'agent' for delegated execution")
    parser.add_argument("--number", type=int, help="Number for rules/skills (e.g., 275)")
    parser.add_argument("--name", type=str, help="Name in kebab-case (e.g., api-versioning)")
    parser.add_argument("--category", type=str, choices=list(CATEGORIES.keys()), help="Category (rules/skills only)")
    parser.add_argument("--globs", type=str, help="Glob pattern for rule (e.g., '*.py')")
    parser.add_argument("--always-apply", action="store_true", help="Make rule always-on")
    parser.add_argument("--model", type=str, choices=list(AGENT_MODELS.keys()), 
                        help="Model for agent (e.g., 'inherit', 'gpt-5.3-codex')")
    parser.add_argument("--readonly", action="store_true", help="Make agent read-only (agents only)")
    parser.add_argument("--background", action="store_true", help="Run agent in background (agents only)")

    args = parser.parse_args()

    # Find .cursor directory
    cursor_dir = find_cursor_dir()
    rules_dir = cursor_dir / "rules"
    skills_dir = cursor_dir / "skills"
    agents_dir = cursor_dir / "agents"

    print("=" * 60)
    print("Rule/Skill/Agent Generator - Using 050-rule-authoring-patterns")
    print("=" * 60)
    print("\nThis script creates STRUCTURE, not CONTENT.")
    print("You fill in the domain expertise.\n")

    # Determine type
    if args.type:
        gen_type = args.type
    else:
        gen_type = prompt_choice(
            "What type are you creating?",
            ["skill (intelligent activation)", "rule (always-on or glob-based)", "agent (delegated execution)"],
        )
        if gen_type.startswith("skill"):
            gen_type = "skill"
        elif gen_type.startswith("rule"):
            gen_type = "rule"
        else:
            gen_type = "agent"

    # Agent flow is simpler - no number or category needed
    if gen_type == "agent":
        # Get name
        if args.name:
            name = args.name
        else:
            name = prompt_user("Agent name (kebab-case, e.g., code-reviewer)")
            name = name.lower().replace(" ", "-").replace("_", "-")

        # Get model
        if args.model:
            model = args.model
        else:
            print("\nAvailable models:")
            for model_id, desc in AGENT_MODELS.items():
                print(f"  {model_id}: {desc}")
            model = prompt_choice("Select model:", list(AGENT_MODELS.keys()))

        # Get optional flags
        readonly = args.readonly
        is_background = args.background

        if not readonly:
            readonly_choice = prompt_user("Read-only mode? (y/n)", "n")
            readonly = readonly_choice.lower() == "y"

        if not is_background:
            bg_choice = prompt_user("Run in background (non-blocking)? (y/n)", "n")
            is_background = bg_choice.lower() == "y"

        generate_agent_structure(agents_dir, name, model, readonly, is_background)
        return

    # Get number
    if args.number is not None:
        number = args.number
    else:
        while True:
            num_str = prompt_user("Number (e.g., 275)")
            if num_str.isdigit() and 0 <= int(num_str) <= 999:
                number = int(num_str)
                break
            print("Please enter a number 0-999")

    # Get name
    if args.name:
        name = args.name
    else:
        name = prompt_user("Name (kebab-case, e.g., api-versioning)")
        name = name.lower().replace(" ", "-").replace("_", "-")

    # Detect or get category
    detected_cat = detect_category_from_number(number)

    if args.category:
        category_key = args.category
    elif detected_cat:
        print(f"\nDetected category from number {number}: {CATEGORIES[detected_cat].name}")
        confirm = prompt_user("Use this category? (y/n)", "y")
        if confirm.lower() == "y":
            category_key = detected_cat
        else:
            category_key = prompt_choice("Select category:", list(CATEGORIES.keys()))
    else:
        category_key = prompt_choice("Select category:", list(CATEGORIES.keys()))

    # Get category info
    category = CATEGORIES[category_key]
    print(f"\nCategory: {category.name}")
    print(f"Token budget: {get_token_budget(number)}")
    print(f"Description: {category.description}")

    # Suggest resources
    print(f"\nSuggested resources for {category.name}:")
    print("  Required:", ", ".join(category.required_resources))
    print("  Optional:", ", ".join(category.optional_resources))

    # Format resource names with topic
    topic = name.split("-")[0] if "-" in name else name
    all_resources = [
        r.replace("{topic}", topic)
        for r in category.required_resources + category.optional_resources
    ]

    selected = prompt_multi_choice("Which resources do you want to create?", all_resources)

    # Generate the structure
    if gen_type == "skill":
        generate_skill_structure(skills_dir, number, name, category_key, selected)
    else:
        # For rules, get activation type
        globs = args.globs
        always_apply = args.always_apply
        
        if not globs and not always_apply:
            activation = prompt_choice(
                "Rule activation type:",
                ["always-on (alwaysApply: true)", "glob-based (e.g., *.py, *.ts)"],
            )
            if activation.startswith("always"):
                always_apply = True
            else:
                globs = prompt_user("Glob pattern (e.g., '*.py' or '*.ts,*.html')")
        
        generate_rule_structure(rules_dir, number, name, category_key, selected, globs, always_apply)


if __name__ == "__main__":
    main()
