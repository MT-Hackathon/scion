# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Map Feature Card success criteria to implemented code locations.

Parses the Feature Interaction Map document and searches for code
that implements each success criterion.
"""

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SuccessCriterion:
    """A single success criterion from a Feature Card."""
    feature_id: str
    feature_name: str
    text: str
    code_files: list[str] = field(default_factory=list)
    status: str = "NOT FOUND"


def parse_feature_map(filepath: Path) -> list[SuccessCriterion]:
    """Parse the Feature Interaction Map for success criteria."""
    criteria: list[SuccessCriterion] = []
    content = filepath.read_text()

    current_feature_id = ""
    current_feature_name = ""
    in_success_criteria = False

    for line in content.split("\n"):
        # Detect feature card headers like "### F-01: Procurement Request Intake"
        feature_match = re.match(r"^### (F-\d+):\s+(.+)", line)
        if feature_match:
            current_feature_id = feature_match.group(1)
            current_feature_name = feature_match.group(2).strip()
            in_success_criteria = False
            continue

        # Detect success criteria section
        if line.strip() == "#### Success Criteria":
            in_success_criteria = True
            continue

        # Detect end of success criteria (next section header)
        if line.startswith("####") and in_success_criteria:
            in_success_criteria = False
            continue

        # Parse criterion lines
        if in_success_criteria and line.strip().startswith("- [ ]"):
            text = line.strip().removeprefix("- [ ]").strip()
            criteria.append(SuccessCriterion(
                feature_id=current_feature_id,
                feature_name=current_feature_name,
                text=text,
            ))

    return criteria


def extract_keywords(text: str) -> list[str]:
    """Extract searchable keywords from a success criterion."""
    keywords = []

    # Look for quoted strings
    quoted = re.findall(r'"([^"]+)"', text)
    keywords.extend(quoted)

    # Look for code-like terms (camelCase, PascalCase, snake_case, UPPER_CASE)
    code_terms = re.findall(r'\b[A-Z][a-zA-Z]+(?:[A-Z][a-zA-Z]*)+\b', text)
    keywords.extend(code_terms)

    code_terms2 = re.findall(r'\b[A-Z_]{3,}\b', text)
    keywords.extend(code_terms2)

    # Look for route paths
    routes = re.findall(r'/[a-z][a-z/-]+', text)
    keywords.extend(routes)

    return list(set(keywords))


def search_codebase(keyword: str, search_dir: str) -> list[str]:
    """Search codebase for a keyword using ripgrep or grep fallback."""
    for cmd in [
        ["rg", "-l", "--no-heading", "-g", "!*.md", "-g", "!node_modules", keyword, search_dir],
        ["grep", "-rl", "--include=*.ts", "--include=*.java", "--include=*.html",
         "--exclude-dir=node_modules", keyword, search_dir],
    ]:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                return [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
            if result.returncode == 1:
                return []
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue
    return []


def map_criterion(criterion: SuccessCriterion, workspace: Path) -> None:
    """Find code that implements a success criterion."""
    keywords = extract_keywords(criterion.text)
    all_files: set[str] = set()

    for keyword in keywords:
        files = search_codebase(keyword, str(workspace))
        all_files.update(files)

    if all_files:
        criterion.code_files = sorted(all_files)[:10]
        criterion.status = "FOUND"
    else:
        criterion.status = "NOT FOUND"


def format_markdown(criteria: list[SuccessCriterion], feature_filter: str | None) -> str:
    """Format results as markdown."""
    lines = ["# Requirements-to-Code Mapping", ""]

    current_feature = ""
    found_count = 0
    total_count = 0

    for c in criteria:
        if feature_filter and c.feature_id != feature_filter.upper():
            continue

        total_count += 1
        if c.status == "FOUND":
            found_count += 1

        if c.feature_id != current_feature:
            current_feature = c.feature_id
            lines.append(f"## {c.feature_id}: {c.feature_name}")
            lines.append("")

        icon = "+" if c.status == "FOUND" else "!"
        lines.append(f"- [{icon}] {c.text}")
        if c.code_files:
            for f in c.code_files[:5]:
                lines.append(f"  - `{f}`")
            if len(c.code_files) > 5:
                lines.append(f"  - ... and {len(c.code_files) - 5} more files")
        else:
            lines.append("  - **NO CODE FOUND** — may need implementation")
        lines.append("")

    pct = (found_count / total_count * 100) if total_count > 0 else 0
    lines.insert(1, f"\nCoverage: {found_count}/{total_count} criteria have matching code ({pct:.0f}%)\n")

    return "\n".join(lines)


def format_json(criteria: list[SuccessCriterion], feature_filter: str | None) -> str:
    """Format results as JSON."""
    import json
    filtered = [c for c in criteria if not feature_filter or c.feature_id == feature_filter.upper()]
    data = [
        {
            "feature_id": c.feature_id,
            "feature_name": c.feature_name,
            "criterion": c.text,
            "status": c.status,
            "code_files": c.code_files,
        }
        for c in filtered
    ]
    return json.dumps(data, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Map Feature Card success criteria to code locations"
    )
    parser.add_argument("--feature", help="Feature Card ID (e.g., F-01)")
    parser.add_argument("--all", action="store_true", help="Map all features")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown",
                        help="Output format (default: markdown)")
    args = parser.parse_args()

    if not args.feature and not args.all:
        parser.error("Either --feature or --all is required")

    workspace = Path.cwd()
    feature_map = workspace / "docs" / "requirements" / "12-feature-interaction-map.md"

    if not feature_map.exists():
        print(f"ERROR: Feature interaction map not found at {feature_map}")
        sys.exit(1)

    criteria = parse_feature_map(feature_map)

    if not criteria:
        print("ERROR: No success criteria found in the feature interaction map")
        sys.exit(1)

    feature_filter = args.feature if not args.all else None

    print(f"Mapping {len(criteria)} success criteria to code...", file=sys.stderr)
    for c in criteria:
        if feature_filter and c.feature_id != feature_filter.upper():
            continue
        map_criterion(c, workspace)

    if args.format == "json":
        print(format_json(criteria, feature_filter))
    else:
        print(format_markdown(criteria, feature_filter))


if __name__ == "__main__":
    main()
