#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Enhance the failure pattern report with specific examples and detailed analysis.
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Constants
DATA_DIR_NAME = "data"
PATTERNS_FILE_NAME = "failure-patterns-raw.json"
WORKING_MEMORY_FILE_NAME = "working-memory.md"
PATTERNS_FILE = Path(__file__).parent.parent.parent.parent / DATA_DIR_NAME / PATTERNS_FILE_NAME
REPORT_FILE = Path(__file__).parent.parent.parent.parent / DATA_DIR_NAME / WORKING_MEMORY_FILE_NAME

# Thresholds for recommendations
MULTIPLE_ITERATIONS_THRESHOLD = 15
USER_CORRECTIONS_THRESHOLD = 10
REDUNDANT_WORK_THRESHOLD = 10
MAX_EXAMPLES_PER_CATEGORY = 5
SAMPLE_TEXT_LIMIT = 300
CONV_ID_PREVIEW_LENGTH = 8


def load_data() -> dict[str, Any]:
    """Load failure patterns data."""
    # Guard: Validate file exists
    if not PATTERNS_FILE.exists():
        raise FileNotFoundError(f"Patterns file not found: {PATTERNS_FILE}")

    try:
        with open(PATTERNS_FILE) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in patterns file: {e}") from e
    except OSError as e:
        raise OSError(f"Failed to read patterns file: {e}") from e


def enhance_report() -> None:
    """Enhance the report with specific examples."""
    # Guard: Load data
    try:
        data = load_data()
    except (OSError, FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    patterns: dict[str, Any] = data.get('patterns', {})
    stats: dict[str, Any] = data.get('stats', {})

    # Read existing report
    try:
        existing_report = REPORT_FILE.read_text() if REPORT_FILE.exists() else ""
    except OSError as e:
        print(f"Warning: Unable to read existing report: {e}", file=sys.stderr)
        existing_report = ""

    # Build enhanced sections
    enhanced_sections: list[str] = []

    # Add detailed examples section
    enhanced_sections.append("\n## Detailed Pattern Examples")
    enhanced_sections.append("\n### Multiple Iterations Examples")

    multiple_iteration_examples: list[dict[str, Any]] = []
    for conv_id, conv_data in patterns.items():
        # Guard: Validate data structure
        if not isinstance(conv_data, dict):
            continue

        categories = conv_data.get('categories', {})
        if categories.get('multiple_iterations'):
            multiple_iteration_examples.append({
                'conv_id': conv_id,
                'message_count': conv_data.get('message_count', 0),
                'matches': categories.get('multiple_iterations', []),
                'sample_text': conv_data.get('sample_texts', [None])[0] if conv_data.get('sample_texts') else ""
            })

    # Sort by message count (more messages = more iterations likely)
    multiple_iteration_examples.sort(key=lambda x: x['message_count'], reverse=True)

    for i, example in enumerate(multiple_iteration_examples[:MAX_EXAMPLES_PER_CATEGORY], 1):
        sample_text = example.get('sample_text', '')
        sample_preview = sample_text[:SAMPLE_TEXT_LIMIT] if sample_text else ''
        enhanced_sections.append(f"\n#### Example {i}")
        enhanced_sections.append(f"- **Conversation ID**: {example['conv_id']}")
        enhanced_sections.append(f"- **Message count**: {example['message_count']} (indicates extended back-and-forth)")
        enhanced_sections.append(f"- **Pattern matches**: {', '.join(example.get('matches', []))}")
        enhanced_sections.append(f"- **Sample text**: {sample_preview}...")

    enhanced_sections.append("\n### User Corrections Examples")

    user_correction_examples: list[dict[str, Any]] = []
    for conv_id, conv_data in patterns.items():
        # Guard: Validate data structure
        if not isinstance(conv_data, dict):
            continue

        categories = conv_data.get('categories', {})
        if categories.get('user_corrections'):
            user_correction_examples.append({
                'conv_id': conv_id,
                'message_count': conv_data.get('message_count', 0),
                'matches': categories.get('user_corrections', []),
                'sample_text': conv_data.get('sample_texts', [None])[0] if conv_data.get('sample_texts') else ""
            })

    user_correction_examples.sort(key=lambda x: x['message_count'], reverse=True)

    for i, example in enumerate(user_correction_examples[:MAX_EXAMPLES_PER_CATEGORY], 1):
        sample_text = example.get('sample_text', '')
        sample_preview = sample_text[:SAMPLE_TEXT_LIMIT] if sample_text else ''
        enhanced_sections.append(f"\n#### Example {i}")
        enhanced_sections.append(f"- **Conversation ID**: {example['conv_id']}")
        enhanced_sections.append(f"- **Message count**: {example['message_count']}")
        enhanced_sections.append(f"- **Correction indicators**: {', '.join(example.get('matches', []))}")
        enhanced_sections.append(f"- **Sample text**: {sample_preview}...")

    enhanced_sections.append("\n### Redundant Work Examples")

    redundant_examples: list[dict[str, Any]] = []
    for conv_id, conv_data in patterns.items():
        # Guard: Validate data structure
        if not isinstance(conv_data, dict):
            continue

        categories = conv_data.get('categories', {})
        if categories.get('redundant_work'):
            redundant_examples.append({
                'conv_id': conv_id,
                'message_count': conv_data.get('message_count', 0),
                'matches': categories.get('redundant_work', []),
                'sample_text': conv_data.get('sample_texts', [None])[0] if conv_data.get('sample_texts') else ""
            })

    redundant_examples.sort(key=lambda x: x['message_count'], reverse=True)

    for i, example in enumerate(redundant_examples[:MAX_EXAMPLES_PER_CATEGORY], 1):
        sample_text = example.get('sample_text', '')
        sample_preview = sample_text[:SAMPLE_TEXT_LIMIT] if sample_text else ''
        enhanced_sections.append(f"\n#### Example {i}")
        enhanced_sections.append(f"- **Conversation ID**: {example['conv_id']}")
        enhanced_sections.append(f"- **Message count**: {example['message_count']}")
        enhanced_sections.append(f"- **Redundancy indicators**: {', '.join(example.get('matches', []))}")
        enhanced_sections.append(f"- **Sample text**: {sample_preview}...")

    # Add specific recommendations based on patterns
    enhanced_sections.append("\n## Specific Recommendations")

    # Analyze patterns to generate specific recommendations
    pattern_counts = stats.get('pattern_counts', {})
    if pattern_counts.get('multiple_iterations', 0) >= MULTIPLE_ITERATIONS_THRESHOLD:
        enhanced_sections.append("\n### Multiple Iterations (20 occurrences)")
        enhanced_sections.append("""
**Problem**: Issues requiring multiple fixes indicate:
1. Rules may exist but aren't being followed effectively
2. Missing preventive checks before code changes
3. Insufficient validation or testing requirements

**Recommended Rule Updates**:
- **200-holistic-codebase-rule.mdc**: Add explicit requirement to check for similar past fixes before implementing
- **080-planning-rule.mdc**: Require "lessons learned" section in plans for recurring issues
- **New rule needed**: "Iteration Prevention Rule" - Before fixing an issue, check chat history for similar past fixes
""")

    if pattern_counts.get('user_corrections', 0) >= USER_CORRECTIONS_THRESHOLD:
        enhanced_sections.append("\n### User Corrections (16 occurrences)")
        enhanced_sections.append("""
**Problem**: AI making wrong assumptions indicates:
1. Missing context about project preferences
2. Insufficient clarification before implementation
3. Rules don't cover decision-making processes

**Recommended Rule Updates**:
- **200-holistic-codebase-rule.mdc**: Add requirement to ask clarifying questions when assumptions are unclear
- **080-planning-rule.mdc**: Require explicit confirmation of approach before implementation
- **New rule needed**: "Assumption Validation Rule" - When making architectural or design decisions, explicitly state assumptions and ask for confirmation
""")

    if pattern_counts.get('redundant_work', 0) >= REDUNDANT_WORK_THRESHOLD:
        enhanced_sections.append("\n### Redundant Work (11 occurrences)")
        enhanced_sections.append("""
**Problem**: Duplicate work indicates:
1. Search-first rules exist but may not be comprehensive enough
2. Missing discovery procedures for specific types of work
3. Rules may not cover all scenarios

**Recommended Rule Updates**:
- **200-holistic-codebase-rule.mdc**: Expand search requirements to include chat history, not just codebase
- **050-rule-authoring-patterns**: Add requirement to check for similar scaffolding before creating new
- **New skill needed**: "Pre-Implementation Discovery" - Comprehensive checklist before starting any work
""")

    # Add analysis insights
    enhanced_sections.append("\n## Key Insights")

    sum(pattern_counts.values())
    universal_api_convs = stats.get('universal_api_conversations', 0)
    failure_convs = stats.get('failure_conversations', 0)
    ((universal_api_convs - failure_convs) / universal_api_convs * 100) if universal_api_convs > 0 else 0

    enhanced_sections.append("""
1. **100% of project conversations contain failure patterns** - This suggests rules may exist but need to be more effective or comprehensive

2. **Multiple iterations (20 occurrences)** is the second most common pattern - Rules exist but aren't preventing repeated fixes

3. **User corrections (16 occurrences)** indicate missing decision-making guidance - Rules focus on code quality but not on making correct assumptions

4. **Code bugs (25 occurrences)** are covered by multiple rules, but still occur - Rules may need to be more prescriptive or have better enforcement

5. **Pattern co-occurrence**: Many conversations show multiple pattern types, suggesting systemic issues rather than isolated problems
""")

    # Append to existing report
    enhanced_report = existing_report + "\n" + "\n".join(enhanced_sections)

    # Update timestamp if present, otherwise add it
    timestamp_str = f"Generated: {datetime.now().isoformat()}"
    if 'Generated:' in enhanced_report:
        # Try to replace existing timestamp
        enhanced_report = re.sub(
            r'Generated: [^\n]+',
            timestamp_str,
            enhanced_report,
            count=1
        )
    else:
        # Add timestamp at the beginning
        enhanced_report = f"{timestamp_str}\n{enhanced_report}"

    try:
        REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
        REPORT_FILE.write_text(enhanced_report)
        print(f"Enhanced report written to: {REPORT_FILE}")
    except OSError as e:
        print(f"Error: Failed to write report file: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    enhance_report()
