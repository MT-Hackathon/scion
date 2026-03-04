#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Reduce oversized rules from 350+ tokens to ≤350 tokens by removing verbose reference descriptions
and compressing explanations while preserving core mandates.

Strategy:
- Remove verbose "Use when/DO NOT use" descriptions in references
- Shorten reference descriptions to single-line summaries
- Compress multi-line explanations to single-line summaries where possible
- Keep all core mandates intact
"""

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
RULES_DIR = PROJECT_ROOT / ".cursor" / "rules"

# Mapping of rules to reduce and the condensed references format
RULE_CONDENSING = {
    "102-ecs-architecture-rule.mdc": {
        "old_ref": (
            "- ECS theory principles and core patterns\n"
            "- Component design and data storage patterns\n"
            "- System composition, error handling, esper patterns\n"
            "- DataFrame performance, migration, and best practices\n"
            "- Data-oriented design optimization techniques (cache)\n"
            "- Storage approach selection procedures (polars vs esper)\n"
            "- Architecture design decisions for ECS patterns\n"
            "- Pipeline save/load patterns"
        ),
        "new_ref": "- <!--ANCHORCONTEXT-ECS-ARCHITECTURE-->: ECS theory and patterns\n- <!--ANCHORCONTEXT-ECS-DATAFRAME-->: DataFrame performance\n- <!--ANCHORSKILLCHOOSE-ECS-STORAGE-->: Storage selection procedures\n- <!--ANCHORPERSONA-ARCHITECT-->: Architecture design decisions\n- <!--ANCHORCONTEXT-DATA-CONTRACTS-->: Pipeline save/load patterns"
    },
    "230-ui-http-communication.mdc": {
        "shorten_refs": True,
        "patterns": [
            (r"<!--ANCHORSKILL-ERROR-ARCHITECTURE-->: Error codes and handling\.", "<!--ANCHORSKILL-ERROR-ARCHITECTURE-->: Error codes and handling."),
            (r"- <!--ANCHORCONTEXT-DATA-CONTRACTS-->: Pipeline node structure\.", "- <!--ANCHORCONTEXT-DATA-CONTRACTS-->: Pipeline structure."),
            (r"- <!--ANCHORSKILL-UI-TECH-STACK-->: [^\\n]+", "- <!--ANCHORSKILL-UI-TECH-STACK-->: UI stack details."),
            (r"- <!--ANCHORSKILL-UI-SECURITY-->: Input validation and credential passing\.", "- <!--ANCHORSKILL-UI-SECURITY-->: Input validation."),
            (r"- <!--ANCHORSKILL-UI-CONFIGURATION-->: Pipeline JSON format\.", "- <!--ANCHORSKILL-UI-CONFIGURATION-->: Pipeline config."),
            (r"- <!--ANCHORSKILL-CROSS-STACK-DEBUGGING-->: [^\\n]+", "- <!--ANCHORSKILL-CROSS-STACK-DEBUGGING-->: HTTP debugging."),
            (r"- <!--ANCHORSKILL-INTEGRATION-TESTING-->: [^\\n]+", "- <!--ANCHORSKILL-INTEGRATION-TESTING-->: API testing."),
            (r"- HTTP implementation skill\.", "- HTTP implementation guidance."),
            (r"- <!--ANCHORCONTEXT-TYPE-SYNC-MAPPINGS-->: [^\\n]+", "- <!--ANCHORCONTEXT-TYPE-SYNC-MAPPINGS-->: Type alignment."),
        ]
    }
}

def condense_rule_file(filepath: Path):
    """Condense a specific rule file."""
    content = filepath.read_text()

    # Strategy 1: Remove verbose reference descriptions (keep only anchor + one-liner)
    # Pattern: remove "Use when... DO NOT use..." from references
    content = re.sub(
        r': ([^\n]+?)\. Use when [^.]+\. DO NOT use [^.]+\.',
        r': \1.',
        content
    )

    # Strategy 2: Shorten overly detailed descriptions
    # Examples like "Terminal usage and conda activation mandate. Use when executing..." → "Terminal usage and activation"
    content = re.sub(
        r'Terminal usage and conda activation mandate',
        r'Terminal usage and activation',
        content
    )

    # Strategy 3: Compress multi-part descriptions
    content = re.sub(
        r': ([^.]+?), with ([^.]+?)\. (Use when|DO NOT)',
        r': \1. \3',
        content,
        flags=re.MULTILINE
    )

    # Strategy 4: Shorten references that end with long context
    content = re.sub(
        r': ([^.]+?) with ([^.]+?)\.(?=\n|$)',
        r': \1.',
        content
    )

    filepath.write_text(content)
    print(f"✓ Condensed {filepath.name}")

def main():
    rules_to_reduce = [
        "102-ecs-architecture-rule.mdc",
        "230-ui-http-communication.mdc",
        "217-ui-styling.mdc",
        "285-fullstack-workflow.mdc",
        "020-mcp-monitoring-rule.mdc",
        "080-planning-rule.mdc",
        "265-integration-testing.mdc",
        "testing-debugging",
        "003-tool-script-paradigm.mdc",
        "150-performance-rule.mdc",
        "211-ui-dev-server-debugging.mdc",
        "105-security-rule.mdc",
    ]

    for rule_name in rules_to_reduce:
        rule_path = RULES_DIR / rule_name
        if rule_path.exists():
            condense_rule_file(rule_path)
        else:
            print(f"⚠ {rule_name} not found")

if __name__ == "__main__":
    main()
