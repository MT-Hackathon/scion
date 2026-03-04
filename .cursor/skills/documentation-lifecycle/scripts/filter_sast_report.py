#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
SAST Report Filter and Summarizer

Filters GitLab SAST (Semgrep) reports to produce actionable summaries.
Removes noise from Info-level and disabled rules, groups by severity.

Usage:
    python filter_sast_report.py [input_path] [--output-dir DIR] [--format json|md|both]

Example:
    python filter_sast_report.py .cursor/docs/gl-sast-report.json --format both
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

# Rules to exclude from filtered output (known noise or intentionally disabled)
# See .cursor/docs/sast-accepted-findings.md for full triage documentation
EXCLUDED_RULES = frozenset({
    "bandit.B101",  # assert statements - design-by-contract pattern
})

# Files with inline nosemgrep comments that have been triaged as false positives
# These are excluded from "actionable" output since they've been reviewed
# NOTE: Cleared for procurement-web. Add triage findings as CI runs and issues are reviewed.
TRIAGED_FILE_RULES: dict[str, frozenset[str]] = {
    # Triage findings for procurement-web will be added as CI runs
}

# Severity levels to exclude (Info is typically noise)
EXCLUDED_SEVERITIES = frozenset({
    "Info",
})

# Severity ordering for sorting (highest first)
SEVERITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Unknown": 4}


def load_report(path: Path) -> dict[str, Any]:
    """Load and validate SAST report JSON."""
    if not path.exists():
        raise FileNotFoundError(f"Report not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if "vulnerabilities" not in data:
        raise ValueError("Invalid SAST report: missing 'vulnerabilities' key")

    return data


def extract_rule_id(vulnerability: dict[str, Any]) -> str:
    """Extract the base rule ID from a vulnerability."""
    cve = vulnerability.get("cve", "")

    # Handle semgrep_id format: "semgrep_id:bandit.B608:line:line"
    if cve.startswith("semgrep_id:"):
        parts = cve.split(":")
        if len(parts) >= 2:
            return parts[1]

    # Fallback: check identifiers
    for identifier in vulnerability.get("identifiers", []):
        if identifier.get("type") == "semgrep_id":
            value = identifier.get("value", "")
            # Extract base rule from "bandit.B608" format
            return value.split(":")[0] if ":" in value else value

    return cve


def should_include(vulnerability: dict[str, Any]) -> bool:
    """Determine if a vulnerability should be included in filtered output."""
    severity = vulnerability.get("severity", "Unknown")
    if severity in EXCLUDED_SEVERITIES:
        return False

    rule_id = extract_rule_id(vulnerability)
    for excluded in EXCLUDED_RULES:
        if excluded in rule_id:
            return False

    # Check if this file+rule combination has been triaged
    location = vulnerability.get("location", {})
    file_path = location.get("file", "")
    if file_path in TRIAGED_FILE_RULES:
        triaged_rules = TRIAGED_FILE_RULES[file_path]
        if any(triaged in rule_id for triaged in triaged_rules):
            return False

    return True


def filter_vulnerabilities(
    vulnerabilities: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Filter vulnerabilities to actionable items only."""
    return [v for v in vulnerabilities if should_include(v)]


def group_by_severity_and_file(
    vulnerabilities: list[dict[str, Any]],
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Group vulnerabilities by severity, then by file."""
    grouped: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: defaultdict(list)
    )

    for vuln in vulnerabilities:
        severity = vuln.get("severity", "Unknown")
        location = vuln.get("location", {})
        file_path = location.get("file", "unknown")
        grouped[severity][file_path].append(vuln)

    # Sort by severity order
    return dict(
        sorted(grouped.items(), key=lambda x: SEVERITY_ORDER.get(x[0], 99))
    )


def generate_summary_stats(
    original: list[dict[str, Any]], filtered: list[dict[str, Any]]
) -> dict[str, Any]:
    """Generate summary statistics."""
    original_by_severity: dict[str, int] = defaultdict(int)
    filtered_by_severity: dict[str, int] = defaultdict(int)

    for v in original:
        original_by_severity[v.get("severity", "Unknown")] += 1

    for v in filtered:
        filtered_by_severity[v.get("severity", "Unknown")] += 1

    return {
        "original_count": len(original),
        "filtered_count": len(filtered),
        "removed_count": len(original) - len(filtered),
        "original_by_severity": dict(original_by_severity),
        "filtered_by_severity": dict(filtered_by_severity),
    }


def format_vulnerability_md(vuln: dict[str, Any], indent: str = "") -> str:
    """Format a single vulnerability as markdown."""
    location = vuln.get("location", {})
    start_line = location.get("start_line", "?")
    end_line = location.get("end_line", start_line)

    line_ref = f"L{start_line}" if start_line == end_line else f"L{start_line}-{end_line}"

    name = vuln.get("name", "Unknown")
    rule_id = extract_rule_id(vuln)
    description = vuln.get("description", "No description")

    # Truncate long descriptions
    if len(description) > 200:
        description = description[:197] + "..."

    return f"""{indent}- **{name}** ({line_ref})
{indent}  - Rule: `{rule_id}`
{indent}  - {description}"""


def generate_markdown_report(
    data: dict[str, Any],
    filtered: list[dict[str, Any]],
    stats: dict[str, Any],
) -> str:
    """Generate a markdown summary report."""
    scan_info = data.get("scan", {})
    start_time = scan_info.get("start_time", "Unknown")

    grouped = group_by_severity_and_file(filtered)

    lines = [
        "# SAST Actionable Findings Report",
        "",
        f"**Generated:** {datetime.now().isoformat()}",
        f"**Scan Time:** {start_time}",
        f"**Scanner:** {scan_info.get('scanner', {}).get('name', 'Unknown')} "
        f"v{scan_info.get('scanner', {}).get('version', '?')}",
        "",
        "## Summary",
        "",
        f"| Metric | Count |",
        f"|--------|-------|",
        f"| Original findings | {stats['original_count']} |",
        f"| Filtered (noise removed) | {stats['removed_count']} |",
        f"| **Actionable findings** | **{stats['filtered_count']}** |",
        "",
        "### By Severity",
        "",
        "| Severity | Count |",
        "|----------|-------|",
    ]

    for severity in ["Critical", "High", "Medium", "Low"]:
        count = stats["filtered_by_severity"].get(severity, 0)
        if count > 0:
            lines.append(f"| {severity} | {count} |")

    lines.extend(["", "---", "", "## Findings by Severity", ""])

    if not filtered:
        lines.append("✅ **No actionable security findings!**")
    else:
        for severity, files in grouped.items():
            lines.append(f"### {severity}")
            lines.append("")

            for file_path, vulns in sorted(files.items()):
                lines.append(f"#### `{file_path}`")
                lines.append("")
                for vuln in sorted(vulns, key=lambda v: v.get("location", {}).get("start_line", 0)):
                    lines.append(format_vulnerability_md(vuln))
                lines.append("")

    lines.extend([
        "---",
        "",
        "## Excluded Rules",
        "",
        "The following rules were filtered out as noise or intentionally disabled:",
        "",
    ])

    for rule in sorted(EXCLUDED_RULES):
        lines.append(f"- `{rule}`")

    lines.extend([
        "",
        f"Info-level findings: {stats['original_by_severity'].get('Info', 0)} (excluded)",
    ])

    return "\n".join(lines)


def generate_filtered_json(
    data: dict[str, Any],
    filtered: list[dict[str, Any]],
    stats: dict[str, Any],
) -> dict[str, Any]:
    """Generate a filtered JSON report."""
    return {
        "version": data.get("version"),
        "scan": data.get("scan"),
        "vulnerabilities": filtered,
        "filter_metadata": {
            "generated": datetime.now().isoformat(),
            "excluded_rules": list(EXCLUDED_RULES),
            "excluded_severities": list(EXCLUDED_SEVERITIES),
            "stats": stats,
        },
    }


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Filter SAST reports to actionable findings",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=".cursor/docs/gl-sast-report.json",
        help="Path to SAST report JSON (default: .cursor/docs/gl-sast-report.json)",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default=".cursor/docs",
        help="Output directory (default: .cursor/docs)",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["json", "md", "both"],
        default="both",
        help="Output format (default: both)",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress console output",
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)

    try:
        data = load_report(input_path)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as e:
        print(f"Error loading report: {e}", file=sys.stderr)
        return 1

    original = data.get("vulnerabilities", [])
    filtered = filter_vulnerabilities(original)
    stats = generate_summary_stats(original, filtered)

    output_dir.mkdir(parents=True, exist_ok=True)

    outputs_written = []

    if args.format in ("json", "both"):
        json_path = output_dir / "sast-actionable.json"
        json_output = generate_filtered_json(data, filtered, stats)
        with json_path.open("w", encoding="utf-8") as f:
            json.dump(json_output, f, indent=2)
        outputs_written.append(str(json_path))

    if args.format in ("md", "both"):
        md_path = output_dir / "sast-actionable.md"
        md_output = generate_markdown_report(data, filtered, stats)
        with md_path.open("w", encoding="utf-8") as f:
            f.write(md_output)
        outputs_written.append(str(md_path))

    if not args.quiet:
        print(f"Original findings: {stats['original_count']}")
        print(f"Noise removed:     {stats['removed_count']}")
        print(f"Actionable:        {stats['filtered_count']}")
        print()
        for severity in ["Critical", "High", "Medium", "Low"]:
            count = stats["filtered_by_severity"].get(severity, 0)
            if count > 0:
                print(f"  {severity}: {count}")
        print()
        print("Output written to:")
        for path in outputs_written:
            print(f"  {path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
