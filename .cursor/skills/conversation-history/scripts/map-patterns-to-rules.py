#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Map failure patterns to existing rules and identify gaps.
"""

import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

# Constants
DATA_DIR_NAME = "data"
RULES_DIR_NAME = "rules"
PATTERNS_FILE_NAME = "failure-patterns-raw.json"
WORKING_MEMORY_FILE_NAME = "working-memory.md"
PATTERNS_FILE = Path(__file__).parent.parent.parent.parent / DATA_DIR_NAME / PATTERNS_FILE_NAME
RULES_DIR = Path(__file__).parent.parent.parent / RULES_DIR_NAME
WORKING_MEMORY_FILE = Path(__file__).parent.parent.parent.parent / DATA_DIR_NAME / WORKING_MEMORY_FILE_NAME

# Thresholds for gap categorization
CRITICAL_COUNT_THRESHOLD = 15
HIGH_COUNT_THRESHOLD = 10
MEDIUM_COUNT_THRESHOLD = 5
COUNT_SEVERITY_THRESHOLDS = [
    (CRITICAL_COUNT_THRESHOLD + 1, 'critical'),
    (HIGH_COUNT_THRESHOLD + 1, 'high'),
    (MEDIUM_COUNT_THRESHOLD + 1, 'medium'),
]
PARTIAL_COVERAGE_THRESHOLDS = [
    (HIGH_COUNT_THRESHOLD + 1, 'high'),
    (MEDIUM_COUNT_THRESHOLD + 1, 'medium'),
]
SEVERITY_RANK = {
    'low': 0,
    'medium': 1,
    'high': 2,
    'critical': 3,
}

# Rule categories and what they cover
RULE_COVERAGE = {
    '100-constitution-rule.mdc': {
        'covers': ['code_bugs', 'testing_anti_patterns'],
        'keywords': ['test', 'guard', 'type', 'function', 'pure', 'immutability']
    },
    '200-holistic-codebase-rule.mdc': {
        'covers': ['redundant_work', 'code_bugs'],
        'keywords': ['search existing', 'grep', 'codebase_search', 'fix code not tests']
    },
    '080-planning-rule.mdc': {
        'covers': ['code_bugs', 'testing_anti_patterns'],
        'keywords': ['test', 'plan', 'edge cases', 'guard']
    },
    '120-python-imports-rule.mdc': {
        'covers': ['code_bugs'],
        'keywords': ['import', 'module', 'src.backend']
    },
    '150-performance-rule.mdc': {
        'covers': ['inefficient_approaches'],
        'keywords': ['performance', 'optimize', 'slow', 'profile']
    },
    '105-security-rule.mdc': {
        'covers': ['code_bugs'],
        'keywords': ['security', 'credential', 'env', 'api key']
    },
    '260-rate-limit-principles.mdc': {
        'covers': ['inefficient_approaches', 'code_bugs'],
        'keywords': ['rate limit', 'api', 'throttle']
    },
    '050-rule-authoring-patterns.mdc': {
        'covers': ['redundant_work'],
        'keywords': ['scaffolding', 'rule', 'authoring', 'overlap', 'consolidation']
    },
    '055-redundancy-detection-rule.mdc': {
        'covers': ['redundant_work'],
        'keywords': ['redundant', 'duplicate', 'overlap']
    },
    '010-terminal-use-rule.mdc': {
        'covers': ['inefficient_approaches'],
        'keywords': ['terminal', 'bash', 'command']
    },
    '015-environment-rule.mdc': {
        'covers': ['code_bugs'],
        'keywords': ['conda', 'environment', 'python', 'venv']
    }
}

# Pattern categories and what they indicate
PATTERN_CATEGORIES = {
    'multiple_iterations': {
        'description': 'Same issue fixed multiple times, repeated debugging',
        'severity': 'high',
        'indicates': 'Missing preventive rules or ineffective existing rules'
    },
    'user_corrections': {
        'description': 'AI made wrong assumptions, user had to correct',
        'severity': 'high',
        'indicates': 'Missing context rules or decision-making guidance'
    },
    'inefficient_approaches': {
        'description': 'Performance issues, wrong algorithms, unnecessary complexity',
        'severity': 'medium',
        'indicates': 'Missing performance rules or optimization guidance'
    },
    'redundant_work': {
        'description': 'Duplicate implementations, redoing existing work',
        'severity': 'high',
        'indicates': 'Missing search-first rules or discovery procedures'
    },
    'code_bugs': {
        'description': 'Test failures, runtime errors, logic errors',
        'severity': 'critical',
        'indicates': 'Missing code quality rules or testing requirements'
    }
}


def load_failure_patterns() -> dict[str, Any]:
    """Load failure patterns from JSON."""
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


def read_rule_file(rule_path: Path) -> str:
    """Read a rule file."""
    # Guard: Validate path
    if not rule_path or not isinstance(rule_path, Path):
        return ""

    try:
        return rule_path.read_text()
    except OSError as e:
        print(f"Warning: Error reading {rule_path}: {e}", file=sys.stderr)
        return ""
    except Exception as e:
        print(f"Warning: Unexpected error reading {rule_path}: {e}", file=sys.stderr)
        return ""


def analyze_pattern_coverage() -> tuple[dict[str, dict[str, Any]], dict[str, int], dict[str, Any]]:
    """Analyze which patterns are covered by which rules."""
    # Guard: Load patterns data
    try:
        patterns_data = load_failure_patterns()
    except (FileNotFoundError, ValueError, OSError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Guard: Verify rules directory exists
    if not RULES_DIR.exists():
        print(f"Error: Rules directory not found: {RULES_DIR}", file=sys.stderr)
        sys.exit(2)

    # Read all rule files
    rules_content: dict[str, str] = {}
    for rule_file in sorted(RULES_DIR.glob("*.mdc")):
        rules_content[rule_file.name] = read_rule_file(rule_file)

    print(f"Loaded {len(rules_content)} rule files")

    # Analyze coverage - initialize with explicit type structure
    coverage_analysis: dict[str, dict[str, Any]] = defaultdict(lambda: {
        'covered_by': [],
        'partially_covered_by': [],
        'not_covered': True
    })

    pattern_counts = patterns_data['stats']['pattern_counts']

    # For each pattern category
    for pattern_category in PATTERN_CATEGORIES:
        if pattern_category not in pattern_counts:
            continue

        # Ensure entry exists before accessing nested keys
        if pattern_category not in coverage_analysis:
            coverage_analysis[pattern_category] = {
                'covered_by': [],
                'partially_covered_by': [],
                'not_covered': True
            }

        # Check which rules cover it
        for rule_file, rule_info in RULE_COVERAGE.items():
            if rule_file not in rules_content:
                continue

            rule_text = rules_content[rule_file].lower()

            # Check if rule explicitly covers this pattern
            if pattern_category in rule_info['covers']:
                coverage_analysis[pattern_category]['covered_by'].append(rule_file)
                coverage_analysis[pattern_category]['not_covered'] = False
            # Check if rule keywords match pattern keywords
            elif any(keyword in rule_text for keyword in rule_info['keywords']):
                # Partial coverage - rule exists but may not prevent the failure
                coverage_analysis[pattern_category]['partially_covered_by'].append(rule_file)

    return coverage_analysis, pattern_counts, patterns_data


def identify_gaps(
    coverage_analysis: dict[str, dict[str, Any]],
    pattern_counts: dict[str, int],
    patterns_data: dict[str, Any]
) -> dict[str, list[dict[str, Any]]]:
    """Identify gaps in rule coverage."""
    gaps: dict[str, list[dict[str, Any]]] = {
        'critical': [],
        'high': [],
        'medium': [],
        'low': []
    }

    # Analyze each pattern category
    for pattern_category, info in PATTERN_CATEGORIES.items():
        coverage = coverage_analysis[pattern_category]
        count = pattern_counts.get(pattern_category, 0)

        if count == 0:
            continue

        gap_info = {
            'pattern': pattern_category,
            'description': info['description'],
            'occurrence_count': count,
            'severity': info['severity'],
            'covered_by': coverage['covered_by'],
            'partially_covered_by': coverage['partially_covered_by'],
            'not_covered': coverage['not_covered'],
            'indicates': info['indicates']
        }

        count_severity = next(
            (label for threshold, label in COUNT_SEVERITY_THRESHOLDS if count >= threshold),
            'low',
        )

        def _higher_severity_label(left: str, right: str) -> str:
            """Return the label with higher severity rank."""
            return left if SEVERITY_RANK[left] >= SEVERITY_RANK[right] else right

        uncovered_gap_severity = _higher_severity_label(info['severity'], count_severity)

        partial_gap_severity = next(
            (label for threshold, label in PARTIAL_COVERAGE_THRESHOLDS if count >= threshold),
            'low',
        )

        if coverage['not_covered'] or (not coverage['covered_by'] and count > MEDIUM_COUNT_THRESHOLD):
            # No coverage or high occurrence without coverage
            gaps[uncovered_gap_severity].append(gap_info)
            continue

        if coverage['partially_covered_by'] and not coverage['covered_by']:
            # Partial coverage only
            gaps[partial_gap_severity].append(gap_info)

    return gaps


def generate_report(
    coverage_analysis: dict[str, dict[str, Any]],
    pattern_counts: dict[str, int],
    patterns_data: dict[str, Any],
    gaps: dict[str, list[dict[str, Any]]]
) -> str:
    """Generate final analysis report."""
    report: list[str] = []
    report.append("# Failure Pattern Analysis and Rules Gap Detection Report")
    report.append(f"\nGenerated: {datetime.now().isoformat()}")
    report.append("\n" + "=" * 80)

    # Executive Summary
    report.append("\n## Executive Summary")
    report.append(f"\n- **Total conversations analyzed**: {patterns_data['stats']['total_conversations']}")
    report.append(f"- **procurement-web conversations**: {patterns_data['stats']['universal_api_conversations']}")
    report.append(f"- **Conversations with failure patterns**: {patterns_data['stats']['failure_conversations']}")
    report.append(f"- **Total failure pattern occurrences**: {sum(pattern_counts.values())}")

    # Pattern Breakdown
    report.append("\n## Pattern Breakdown")
    report.append("\n| Pattern Category | Occurrences | Severity |")
    report.append("|-----------------|-------------|----------|")
    for pattern, count in sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True):
        severity = PATTERN_CATEGORIES[pattern]['severity']
        report.append(f"| {pattern} | {count} | {severity} |")

    # Coverage Analysis
    report.append("\n## Coverage Analysis")
    for pattern_category in sorted(PATTERN_CATEGORIES.keys()):
        if pattern_category not in pattern_counts:
            continue

        coverage = coverage_analysis[pattern_category]
        report.append(f"\n### {pattern_category}")
        report.append(f"- **Description**: {PATTERN_CATEGORIES[pattern_category]['description']}")
        report.append(f"- **Occurrences**: {pattern_counts[pattern_category]}")

        if coverage['covered_by']:
            report.append(f"- **Covered by**: {', '.join(coverage['covered_by'])}")
        if coverage['partially_covered_by']:
            report.append(f"- **Partially covered by**: {', '.join(coverage['partially_covered_by'])}")
        coverage_status = {
            (False, True): "- **Status**: ❌ NOT COVERED",
            (True, True): "- **Status**: ✅ COVERED",
            (True, False): "- **Status**: ✅ COVERED",
        }.get(
            (bool(coverage['covered_by']), bool(coverage['not_covered'])),
            "- **Status**: ⚠️ PARTIALLY COVERED",
        )
        report.append(coverage_status)

    # Gap Analysis
    report.append("\n## Gap Analysis")

    for severity_level in ['critical', 'high', 'medium', 'low']:
        if gaps[severity_level]:
            report.append(f"\n### {severity_level.upper()} Priority Gaps")
            for gap in gaps[severity_level]:
                report.append(f"\n#### {gap['pattern']}")
                report.append(f"- **Description**: {gap['description']}")
                report.append(f"- **Occurrences**: {gap['occurrence_count']}")
                report.append(f"- **Indicates**: {gap['indicates']}")
                def _report_covered() -> None:
                    report.append(f"- **Currently covered by**: {', '.join(gap['covered_by'])}")

                def _report_partial() -> None:
                    report.append(f"- **Partially covered by**: {', '.join(gap['partially_covered_by'])}")
                    report.append("- **Issue**: Rule exists but may not be effective at preventing this failure")

                def _report_none() -> None:
                    report.append("- **Issue**: No rule coverage")

                coverage_reporters = {
                    'covered_by': _report_covered,
                    'partially_covered_by': _report_partial,
                    'none': _report_none,
                }
                coverage_key = next(
                    (key for key in ('covered_by', 'partially_covered_by') if gap[key]),
                    'none',
                )
                coverage_reporters[coverage_key]()
                report.append(f"- **Recommendation**: {'Update existing rules' if gap['partially_covered_by'] else 'Create new rule'} to address this pattern")

    # Recommendations
    report.append("\n## Recommendations")

    # Count gaps by type
    new_rules_needed = sum(1 for severity in gaps.values() for gap in severity if not gap['partially_covered_by'] and not gap['covered_by'])
    rule_updates_needed = sum(1 for severity in gaps.values() for gap in severity if gap['partially_covered_by'])

    report.append("\n### Summary")
    report.append(f"- **New rules needed**: {new_rules_needed}")
    report.append(f"- **Rule updates needed**: {rule_updates_needed}")

    report.append("\n### Action Items")
    report.append("\n1. **Critical Priority**: Address gaps that caused significant wasted time")
    report.append("2. **High Priority**: Address gaps that caused user corrections or inefficient work")
    report.append("3. **Review Rule Effectiveness**: Patterns that occurred despite existing rules need rule updates")
    report.append("4. **Process Improvements**: Add rules for common failure patterns")

    return "\n".join(report)


if __name__ == "__main__":
    try:
        coverage_analysis, pattern_counts, patterns_data = analyze_pattern_coverage()
        gaps = identify_gaps(coverage_analysis, pattern_counts, patterns_data)
        report = generate_report(coverage_analysis, pattern_counts, patterns_data, gaps)

        # Write report
        output_file = WORKING_MEMORY_FILE
        output_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            output_file.write_text(report)
            print(f"Report generated: {output_file}")

            # Print summary
            print("\n" + "=" * 80)
            print("SUMMARY")
            print("=" * 80)
            print(f"Total patterns found: {sum(pattern_counts.values())}")
            print(f"Critical gaps: {len(gaps['critical'])}")
            print(f"High priority gaps: {len(gaps['high'])}")
            print(f"Medium priority gaps: {len(gaps['medium'])}")
            print(f"Low priority gaps: {len(gaps['low'])}")
        except OSError as e:
            print(f"Error: Failed to write report file: {e}", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"Error: Unexpected error during analysis: {e}", file=sys.stderr)
        sys.exit(1)
