#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

"""Build a compressed knowledge map for a Rootstock .cursor environment."""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

EXIT_SUCCESS = 0
EXIT_ERROR = 1

CURSOR_DIRNAME = ".cursor"
BASE_BRANCH = "main"
DEFAULT_OUTPUT_DIR = Path(".rootstock") / "reports"
DATE_FORMAT = "%Y-%m-%d"

SKILL_FILENAME = "SKILL.md"
RULE_FILENAME = "RULE.mdc"
AGENT_SUFFIX = ".md"

FRONTMATTER_DELIMITER = "---"
GIT_TIMEOUT_SECONDS = 120
LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
HEADING_PATTERN = re.compile(r"^\s*#{1,6}\s+(.+?)\s*$")
WORD_PATTERN = re.compile(r"[a-zA-Z][a-zA-Z0-9-]*")

STOP_WORDS = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "not",
    "to",
    "of",
    "in",
    "on",
    "at",
    "as",
    "by",
    "for",
    "with",
    "from",
    "into",
    "over",
    "under",
    "use",
    "when",
    "see",
    "do",
    "does",
    "dont",
    "don't",
    "this",
    "that",
    "these",
    "those",
    "also",
    "any",
    "all",
    "be",
    "is",
    "are",
    "was",
    "were",
    "been",
    "being",
    "have",
    "has",
    "had",
    "having",
    "it",
    "its",
    "we",
    "you",
    "your",
    "our",
    "their",
    "they",
    "them",
    "if",
    "but",
    "can",
    "will",
    "should",
    "must",
    "across",
    "within",
    "via",
    "without",
    "about",
}


@dataclass(frozen=True)
class FileMetrics:
    """Basic text metrics for a tracked file."""

    path: str
    lines: int
    chars: int
    estimated_tokens: int
    content: str


@dataclass(frozen=True)
class SkillMap:
    """Normalized skill record for map generation."""

    name: str
    description: str
    lines: int
    estimated_tokens: int
    cross_references: list[str]
    headings: list[str]
    description_keywords: set[str]
    concept_keywords: set[str]


@dataclass(frozen=True)
class RuleMap:
    """Normalized rule record for map generation."""

    name: str
    description: str
    activation: str
    lines: int
    estimated_tokens: int
    cross_references: list[str]
    keywords: set[str]


@dataclass(frozen=True)
class AgentMap:
    """Normalized agent record for map generation."""

    name: str
    description: str
    lines: int
    cross_references: list[str]


def emit_json(payload: dict[str, object]) -> None:
    """Emit machine-readable JSON payload to stdout."""
    print(json.dumps(payload, indent=2))


def log(message: str) -> None:
    """Emit human-readable status to stderr."""
    sys.stderr.write(f"{message}\n")


def fail(message: str, payload: dict[str, object] | None = None) -> int:
    """Emit standardized error payload and stderr message."""
    result = payload if payload is not None else {}
    result["status"] = "error"
    result["error"] = message
    emit_json(result)
    log(f"ERROR: {message}")
    return EXIT_ERROR


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        prog="knowledge-map.py",
        description=(
            "Scan a Rootstock .cursor environment and generate a compressed knowledge map "
            "with concept index, quality audit, coverage, and size metrics."
        ),
    )
    parser.add_argument(
        "--rootstock-repo",
        type=Path,
        required=True,
        help="Path to local Rootstock repository clone.",
    )
    parser.add_argument(
        "--branch",
        default=BASE_BRANCH,
        help="Branch to analyze (default: main).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory to write reports (default: .rootstock/reports/ under rootstock repo).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logs.",
    )
    return parser.parse_args(argv)


def ensure_directory(path: Path, label: str) -> None:
    """Validate that a path exists and is a directory."""
    if not path.exists():
        raise ValueError(f"{label} does not exist: {path}")
    if not path.is_dir():
        raise ValueError(f"{label} is not a directory: {path}")


def run_git(
    repo_path: Path,
    args: list[str],
    verbose: bool,
    allow_failure: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run git command in repository path."""
    command = ["git", *args]
    if verbose:
        log(f"[git] {repo_path}: {' '.join(command)}")
    try:
        completed = subprocess.run(
            command,
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False,
            encoding="utf-8",
            errors="replace",
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"git {' '.join(args)} timed out after {GIT_TIMEOUT_SECONDS}s"
        ) from exc
    if completed.returncode == 0:
        return completed
    if allow_failure:
        return completed
    stderr = completed.stderr.strip()
    stdout = completed.stdout.strip()
    details = stderr if stderr != "" else stdout
    if details == "":
        details = "git command failed without output"
    raise RuntimeError(f"git {' '.join(args)} failed: {details}")


def ensure_git_repository(repo_path: Path, verbose: bool) -> None:
    """Validate that path is a git work tree."""
    completed = run_git(
        repo_path=repo_path,
        args=["rev-parse", "--is-inside-work-tree"],
        verbose=verbose,
        allow_failure=True,
    )
    if completed.returncode != 0:
        raise ValueError(f"Not a git repository: {repo_path}")
    if completed.stdout.strip().lower() != "true":
        raise ValueError(f"Path is not inside a git work tree: {repo_path}")


def branch_exists(repo_path: Path, branch: str, verbose: bool) -> bool:
    """Check whether local branch exists."""
    completed = run_git(
        repo_path=repo_path,
        args=["show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
        verbose=verbose,
        allow_failure=True,
    )
    return completed.returncode == 0


def resolve_output_dir(rootstock_repo: Path, output_dir: Path | None) -> Path:
    """Resolve output path with repo-relative default behavior."""
    if output_dir is None:
        return rootstock_repo / DEFAULT_OUTPUT_DIR
    if output_dir.is_absolute():
        return output_dir
    return rootstock_repo / output_dir


def estimate_tokens(char_count: int) -> int:
    """Estimate token count using rough 4 chars/token conversion."""
    if char_count <= 0:
        return 0
    return (char_count + 3) // 4


def count_lines(text: str) -> int:
    """Count text lines."""
    if text == "":
        return 0
    return len(text.splitlines())


def list_cursor_files(repo_path: Path, branch: str, verbose: bool) -> list[str]:
    """List all files tracked under .cursor on branch."""
    completed = run_git(
        repo_path=repo_path,
        args=["ls-tree", "-r", "--name-only", branch, CURSOR_DIRNAME],
        verbose=verbose,
    )
    files = [line.strip() for line in completed.stdout.splitlines() if line.strip() != ""]
    return sorted(files)


def read_branch_file(repo_path: Path, branch: str, path_text: str, verbose: bool) -> str:
    """Read file content from branch:path using git show."""
    completed = run_git(
        repo_path=repo_path,
        args=["show", f"{branch}:{path_text}"],
        verbose=verbose,
    )
    return completed.stdout


def parse_frontmatter(text: str) -> tuple[dict[str, object], str]:
    """Parse YAML-like frontmatter with simple key/value and list support."""
    lines = text.splitlines()
    if not lines:
        return {}, text
    if lines[0].strip() != FRONTMATTER_DELIMITER:
        return {}, text

    closing_index: int | None = None
    for index in range(1, len(lines)):
        if lines[index].strip() == FRONTMATTER_DELIMITER:
            closing_index = index
            break
    if closing_index is None:
        return {}, text

    raw_meta = lines[1:closing_index]
    body = "\n".join(lines[closing_index + 1 :])
    parsed: dict[str, object] = {}
    active_list_key: str | None = None

    for raw_line in raw_meta:
        line = raw_line.rstrip()
        stripped = line.strip()
        if stripped == "" or stripped.startswith("#"):
            continue
        if stripped.startswith("- ") and active_list_key is not None:
            current = parsed.get(active_list_key, [])
            if not isinstance(current, list):
                current = []
            value = normalize_frontmatter_scalar(stripped[2:].strip())
            if isinstance(value, str):
                current.append(value)
            parsed[active_list_key] = current
            continue

        active_list_key = None
        if ":" not in stripped:
            continue
        key, raw_value = stripped.split(":", 1)
        key = key.strip()
        value_text = raw_value.strip()
        if value_text == "":
            parsed[key] = []
            active_list_key = key
            continue
        parsed[key] = normalize_frontmatter_scalar(value_text)
    return parsed, body


def normalize_frontmatter_scalar(value_text: str) -> object:
    """Normalize simple YAML scalars to Python values."""
    lowered = value_text.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if (
        (value_text.startswith('"') and value_text.endswith('"'))
        or (value_text.startswith("'") and value_text.endswith("'"))
    ) and len(value_text) >= 2:
        return value_text[1:-1]
    return value_text


def stringify_frontmatter_value(value: object) -> str:
    """Coerce frontmatter value to normalized string."""
    if isinstance(value, str):
        return value.strip()
    return ""


def infer_rule_activation(frontmatter: dict[str, object]) -> str:
    """Infer rule activation mode from frontmatter keys."""
    always_apply = frontmatter.get("alwaysApply")
    if isinstance(always_apply, bool) and always_apply:
        return "alwaysApply"
    globs_value = frontmatter.get("globs")
    if isinstance(globs_value, list) and len(globs_value) > 0:
        return "globs"
    if isinstance(globs_value, str) and globs_value.strip() != "":
        return "globs"
    return "manual"


def extract_cross_references(text: str) -> list[str]:
    """Extract linked skill/rule references from markdown links."""
    references: set[str] = set()
    for match in LINK_PATTERN.findall(text):
        target = match.strip()
        if target == "":
            continue
        normalized = target.replace("\\", "/")
        skill_match = re.search(r"(?:^|/)skills/([^/]+)/", normalized)
        if skill_match is not None:
            references.add(f"skill:{skill_match.group(1)}")
            continue
        local_skill_match = re.search(r"\.\./([^/]+)/SKILL\.md$", normalized)
        if local_skill_match is not None:
            references.add(f"skill:{local_skill_match.group(1)}")
            continue
        rule_match = re.search(r"(?:^|/)rules/([^/]+)/", normalized)
        if rule_match is not None:
            references.add(f"rule:{rule_match.group(1)}")
            continue
        local_rule_match = re.search(r"\.\./([^/]+)/RULE\.mdc$", normalized)
        if local_rule_match is not None:
            references.add(f"rule:{local_rule_match.group(1)}")
    return sorted(references)


def extract_headings(markdown_text: str) -> list[str]:
    """Extract markdown heading text as concept indicators."""
    headings: list[str] = []
    for line in markdown_text.splitlines():
        match = HEADING_PATTERN.match(line)
        if match is None:
            continue
        heading = match.group(1).strip()
        if heading != "":
            headings.append(heading)
    return headings


def tokenize_keywords(text: str) -> set[str]:
    """Tokenize and normalize keyword set from text."""
    tokens: set[str] = set()
    for match in WORD_PATTERN.findall(text.lower()):
        word = match.strip("-")
        if word == "":
            continue
        if word in STOP_WORDS:
            continue
        tokens.add(word)
    return tokens


def description_token_count(description: str) -> int:
    """Count words in a description."""
    if description.strip() == "":
        return 0
    return len([token for token in description.split() if token.strip() != ""])


def infer_domains(skill_name: str, concept_keywords: set[str]) -> set[str]:
    """Infer domain labels from skill name and concept keywords."""
    domains: set[str] = set()
    name = skill_name.lower()
    keywords_text = " ".join(sorted(concept_keywords))

    if name.startswith("angular-") or "angular" in keywords_text:
        domains.add("angular")
    if name.startswith("ui-") or "frontend" in keywords_text or "svelte" in keywords_text:
        domains.add("ui")
    if name.startswith("java-") or "spring" in keywords_text or "java" in keywords_text:
        domains.add("java")
    if "testing" in name or "debugging" in name or "testing" in keywords_text:
        domains.add("testing")
    if "security" in name or "security" in keywords_text or "auth" in keywords_text:
        domains.add("security")
    if "data" in name or "schema" in keywords_text or "contract" in keywords_text:
        domains.add("data")
    if "git" in name or "workflow" in keywords_text or "rootstock" in name:
        domains.add("workflow")
    if "planning" in name or "delegation" in name or "architecture" in keywords_text:
        domains.add("planning")
    if "container" in name or "docker" in keywords_text or "podman" in keywords_text:
        domains.add("infrastructure")
    if not domains:
        domains.add("general")
    return domains


def load_file_metrics(
    repo_path: Path,
    branch: str,
    file_paths: list[str],
    verbose: bool,
) -> dict[str, FileMetrics]:
    """Load file content and metrics for each .cursor tracked path."""
    metrics: dict[str, FileMetrics] = {}
    for path_text in file_paths:
        content = read_branch_file(repo_path, branch, path_text, verbose)
        chars = len(content)
        lines = count_lines(content)
        metrics[path_text] = FileMetrics(
            path=path_text,
            lines=lines,
            chars=chars,
            estimated_tokens=estimate_tokens(chars),
            content=content,
        )
    return metrics


def build_skill_maps(file_metrics: dict[str, FileMetrics]) -> list[SkillMap]:
    """Build normalized skill records from tracked files."""
    skills_by_name: dict[str, list[FileMetrics]] = defaultdict(list)
    for path_text, metrics in file_metrics.items():
        path = PurePosixPath(path_text)
        if len(path.parts) < 4:
            continue
        if path.parts[0] != CURSOR_DIRNAME or path.parts[1] != "skills":
            continue
        skill_name = path.parts[2]
        skills_by_name[skill_name].append(metrics)

    skill_maps: list[SkillMap] = []
    for skill_name in sorted(skills_by_name.keys()):
        files = skills_by_name[skill_name]
        doc_path = f"{CURSOR_DIRNAME}/skills/{skill_name}/{SKILL_FILENAME}"
        doc_metrics = file_metrics.get(doc_path)
        if doc_metrics is None:
            continue

        frontmatter, body = parse_frontmatter(doc_metrics.content)
        description = stringify_frontmatter_value(frontmatter.get("description", ""))
        headings = extract_headings(body)

        combined_cross_refs: set[str] = set()
        for file_record in files:
            combined_cross_refs.update(extract_cross_references(file_record.content))

        description_keywords = tokenize_keywords(description)
        heading_keywords: set[str] = set()
        for heading in headings:
            heading_keywords.update(tokenize_keywords(heading))
        concept_keywords = set(description_keywords)
        concept_keywords.update(heading_keywords)

        total_lines = sum(file_record.lines for file_record in files)
        total_tokens = sum(file_record.estimated_tokens for file_record in files)

        skill_maps.append(
            SkillMap(
                name=skill_name,
                description=description,
                lines=total_lines,
                estimated_tokens=total_tokens,
                cross_references=sorted(combined_cross_refs),
                headings=headings,
                description_keywords=description_keywords,
                concept_keywords=concept_keywords,
            )
        )
    return skill_maps


def build_rule_maps(file_metrics: dict[str, FileMetrics]) -> list[RuleMap]:
    """Build normalized rule records from RULE.mdc files."""
    rule_maps: list[RuleMap] = []
    for path_text, metrics in sorted(file_metrics.items(), key=lambda item: item[0]):
        path = PurePosixPath(path_text)
        if len(path.parts) != 4:
            continue
        if path.parts[0] != CURSOR_DIRNAME or path.parts[1] != "rules":
            continue
        if path.parts[3] != RULE_FILENAME:
            continue
        rule_name = path.parts[2]
        frontmatter, _ = parse_frontmatter(metrics.content)
        description = stringify_frontmatter_value(frontmatter.get("description", ""))
        activation = infer_rule_activation(frontmatter)
        keywords = tokenize_keywords(description)
        cross_references = extract_cross_references(metrics.content)
        rule_maps.append(
            RuleMap(
                name=rule_name,
                description=description,
                activation=activation,
                lines=metrics.lines,
                estimated_tokens=metrics.estimated_tokens,
                cross_references=cross_references,
                keywords=keywords,
            )
        )
    return rule_maps


def build_agent_maps(file_metrics: dict[str, FileMetrics]) -> list[AgentMap]:
    """Build normalized agent records from .cursor/agents/*.md."""
    agent_maps: list[AgentMap] = []
    for path_text, metrics in sorted(file_metrics.items(), key=lambda item: item[0]):
        path = PurePosixPath(path_text)
        if len(path.parts) != 3:
            continue
        if path.parts[0] != CURSOR_DIRNAME or path.parts[1] != "agents":
            continue
        if path.suffix.lower() != AGENT_SUFFIX:
            continue
        frontmatter, _ = parse_frontmatter(metrics.content)
        description = stringify_frontmatter_value(frontmatter.get("description", ""))
        if description == "":
            description = f"Agent definition {path.name}"
        agent_maps.append(
            AgentMap(
                name=path.stem,
                description=description,
                lines=metrics.lines,
                cross_references=extract_cross_references(metrics.content),
            )
        )
    return agent_maps


def build_concept_index(skills: list[SkillMap], rules: list[RuleMap]) -> dict[str, list[str]]:
    """Build reverse keyword index over skills and rules."""
    concept_map: dict[str, set[str]] = defaultdict(set)
    for skill in skills:
        for keyword in skill.concept_keywords:
            concept_map[keyword].add(skill.name)
    for rule in rules:
        for keyword in rule.keywords:
            concept_map[keyword].add(rule.name)
    filtered: dict[str, list[str]] = {}
    for keyword in sorted(concept_map.keys()):
        owners = sorted(concept_map[keyword])
        if len(owners) < 2:
            continue
        filtered[keyword] = owners
    return filtered


def build_description_audit(skills: list[SkillMap]) -> dict[str, object]:
    """Build description quality findings for skills."""
    under_utilized: list[dict[str, object]] = []
    missing_delineation: list[dict[str, object]] = []
    overlapping: list[dict[str, object]] = []

    for skill in skills:
        token_count = description_token_count(skill.description)
        if token_count < 20:
            under_utilized.append(
                {
                    "name": skill.name,
                    "token_count": token_count,
                    "description": skill.description,
                }
            )
        lowered = skill.description.lower()
        has_use_when = "use when" in lowered
        has_do_not_use = "do not use" in lowered
        if not has_use_when and not has_do_not_use:
            missing_delineation.append(
                {
                    "name": skill.name,
                    "description": skill.description,
                }
            )

    sorted_skills = sorted(skills, key=lambda item: item.name)
    for index, skill_a in enumerate(sorted_skills):
        for skill_b in sorted_skills[index + 1 :]:
            if not skill_a.description_keywords or not skill_b.description_keywords:
                continue
            shared = sorted(skill_a.description_keywords.intersection(skill_b.description_keywords))
            if not shared:
                continue
            denominator = min(len(skill_a.description_keywords), len(skill_b.description_keywords))
            if denominator == 0:
                continue
            overlap_ratio = len(shared) / denominator
            if overlap_ratio <= 0.5:
                continue
            overlapping.append(
                {
                    "skill_a": skill_a.name,
                    "skill_b": skill_b.name,
                    "shared_keywords": shared,
                }
            )

    return {
        "under_utilized": under_utilized,
        "missing_delineation": missing_delineation,
        "overlapping": overlapping,
    }


def build_coverage_map(skills: list[SkillMap]) -> dict[str, dict[str, object]]:
    """Group skills into inferred domains and classify coverage depth."""
    domain_to_skills: dict[str, set[str]] = defaultdict(set)
    for skill in skills:
        for domain in infer_domains(skill.name, skill.concept_keywords):
            domain_to_skills[domain].add(skill.name)

    coverage_map: dict[str, dict[str, object]] = {}
    for domain in sorted(domain_to_skills.keys()):
        skill_names = sorted(domain_to_skills[domain])
        coverage_map[domain] = {
            "skills": skill_names,
            "depth": "deep" if len(skill_names) > 1 else "thin",
        }
    return coverage_map


def build_cross_reference_graph(skills: list[SkillMap]) -> dict[str, object]:
    """Build directed skill-reference graph and list isolated skills."""
    skill_names = {skill.name for skill in skills}
    outgoing: dict[str, list[str]] = {}
    incoming_count: dict[str, int] = {name: 0 for name in skill_names}

    for skill in skills:
        targets: set[str] = set()
        for reference in skill.cross_references:
            if not reference.startswith("skill:"):
                continue
            target_name = reference.split(":", 1)[1]
            if target_name in skill_names and target_name != skill.name:
                targets.add(target_name)
        ordered_targets = sorted(targets)
        outgoing[skill.name] = ordered_targets
        for target in ordered_targets:
            incoming_count[target] += 1

    isolated = [
        name
        for name in sorted(skill_names)
        if len(outgoing.get(name, [])) == 0 and incoming_count.get(name, 0) == 0
    ]
    return {
        "references": outgoing,
        "isolated_skills": isolated,
    }


def build_markdown_summary(report: dict[str, object]) -> str:
    """Render concise human-readable markdown for the knowledge map."""
    metadata = report.get("metadata", {})
    concept_index = report.get("concept_index", {})
    description_audit = report.get("description_audit", {})
    coverage_map = report.get("coverage_map", {})
    skills = report.get("skills", [])
    rules = report.get("rules", [])
    cross_graph = report.get("cross_reference_graph", {})

    if not isinstance(metadata, dict):
        raise ValueError("Invalid report metadata for markdown.")

    lines: list[str] = []
    lines.append("# Knowledge Map")
    lines.append("")
    lines.append(f"- Branch: `{metadata.get('branch', '')}`")
    lines.append(f"- Timestamp: `{metadata.get('timestamp', '')}`")
    lines.append(f"- Skills: `{metadata.get('total_skills', 0)}`")
    lines.append(f"- Rules: `{metadata.get('total_rules', 0)}`")
    lines.append(f"- Agents: `{metadata.get('total_agents', 0)}`")
    lines.append(f"- Files: `{metadata.get('total_files', 0)}`")
    lines.append(f"- Estimated tokens: `{metadata.get('total_estimated_tokens', 0)}`")
    lines.append(f"- Always-on tokens: `{metadata.get('always_on_tokens', 0)}`")
    lines.append("")

    under_count = len(description_audit.get("under_utilized", [])) if isinstance(description_audit, dict) else 0
    missing_count = (
        len(description_audit.get("missing_delineation", []))
        if isinstance(description_audit, dict)
        else 0
    )
    overlap_count = len(description_audit.get("overlapping", [])) if isinstance(description_audit, dict) else 0

    lines.append("## Description Audit")
    lines.append("")
    lines.append(f"- Under-utilized descriptions (<20 tokens): `{under_count}`")
    lines.append(f"- Missing delineation patterns: `{missing_count}`")
    lines.append(f"- Potential description overlaps (>50%): `{overlap_count}`")
    lines.append("")

    lines.append("## Coverage Map")
    lines.append("")
    if isinstance(coverage_map, dict) and coverage_map:
        for domain in sorted(coverage_map.keys()):
            entry = coverage_map.get(domain, {})
            if not isinstance(entry, dict):
                continue
            skills_in_domain = entry.get("skills", [])
            depth = entry.get("depth", "thin")
            lines.append(f"- `{domain}`: `{depth}` ({len(skills_in_domain)} skills)")
    else:
        lines.append("- No domains inferred.")
    lines.append("")

    lines.append("## Cross References")
    lines.append("")
    isolated = cross_graph.get("isolated_skills", []) if isinstance(cross_graph, dict) else []
    if isinstance(isolated, list) and isolated:
        lines.append(f"- Isolated skills: {', '.join(f'`{name}`' for name in isolated)}")
    else:
        lines.append("- Isolated skills: none")
    lines.append("")

    lines.append("## Top Concepts")
    lines.append("")
    if isinstance(concept_index, dict) and concept_index:
        ordered = sorted(
            concept_index.items(),
            key=lambda item: (-len(item[1]), item[0]),
        )
        for keyword, owners in ordered[:30]:
            lines.append(f"- `{keyword}`: {', '.join(f'`{name}`' for name in owners)}")
    else:
        lines.append("- No shared concept keywords found.")
    lines.append("")

    lines.append("## Largest Skills")
    lines.append("")
    if isinstance(skills, list) and skills:
        ordered_skills = sorted(
            [item for item in skills if isinstance(item, dict)],
            key=lambda item: int(item.get("estimated_tokens", 0)),
            reverse=True,
        )
        for item in ordered_skills[:10]:
            lines.append(f"- `{item.get('name', '')}`: {item.get('estimated_tokens', 0)} tokens")
    else:
        lines.append("- No skill records.")
    lines.append("")

    lines.append("## Rules")
    lines.append("")
    if isinstance(rules, list) and rules:
        for item in sorted([entry for entry in rules if isinstance(entry, dict)], key=lambda entry: str(entry.get("name", ""))):
            lines.append(
                f"- `{item.get('name', '')}` ({item.get('activation', 'manual')}): "
                f"{item.get('estimated_tokens', 0)} tokens"
            )
    else:
        lines.append("- No rule records.")
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_report(
    branch: str,
    file_metrics: dict[str, FileMetrics],
    skills: list[SkillMap],
    rules: list[RuleMap],
    agents: list[AgentMap],
) -> dict[str, object]:
    """Build complete knowledge map payload."""
    total_files = len(file_metrics)
    total_lines = sum(metrics.lines for metrics in file_metrics.values())
    total_tokens = sum(metrics.estimated_tokens for metrics in file_metrics.values())
    always_on_tokens = sum(
        rule.estimated_tokens for rule in rules if rule.activation == "alwaysApply"
    )

    concept_index = build_concept_index(skills, rules)
    description_audit = build_description_audit(skills)
    coverage_map = build_coverage_map(skills)
    cross_graph = build_cross_reference_graph(skills)

    return {
        "metadata": {
            "branch": branch,
            "timestamp": datetime.now(UTC).isoformat(),
            "total_skills": len(skills),
            "total_rules": len(rules),
            "total_agents": len(agents),
            "total_files": total_files,
            "total_lines": total_lines,
            "total_estimated_tokens": total_tokens,
            "always_on_tokens": always_on_tokens,
        },
        "concept_index": concept_index,
        "description_audit": description_audit,
        "coverage_map": coverage_map,
        "cross_reference_graph": cross_graph,
        "skills": [
            {
                "name": skill.name,
                "description": skill.description,
                "lines": skill.lines,
                "estimated_tokens": skill.estimated_tokens,
                "cross_references": skill.cross_references,
                "headings": skill.headings,
            }
            for skill in skills
        ],
        "rules": [
            {
                "name": rule.name,
                "description": rule.description,
                "activation": rule.activation,
                "lines": rule.lines,
                "estimated_tokens": rule.estimated_tokens,
            }
            for rule in rules
        ],
        "agents": [
            {
                "name": agent.name,
                "description": agent.description,
                "lines": agent.lines,
                "cross_references": agent.cross_references,
            }
            for agent in agents
        ],
    }


def write_reports(
    output_dir: Path,
    report: dict[str, object],
) -> tuple[Path, Path]:
    """Write JSON and markdown reports."""
    output_dir.mkdir(parents=True, exist_ok=True)
    date_token = datetime.now(UTC).strftime(DATE_FORMAT)
    json_path = output_dir / f"knowledge-map-{date_token}.json"
    markdown_path = output_dir / f"knowledge-map-{date_token}.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    markdown_path.write_text(build_markdown_summary(report), encoding="utf-8")
    return json_path, markdown_path


def print_human_summary(
    report: dict[str, object],
    json_path: Path,
    markdown_path: Path,
) -> None:
    """Emit concise human summary to stderr."""
    metadata = report.get("metadata", {})
    if not isinstance(metadata, dict):
        return
    log(
        "Knowledge map complete. "
        f"branch={metadata.get('branch', '')} "
        f"skills={metadata.get('total_skills', 0)} "
        f"rules={metadata.get('total_rules', 0)} "
        f"agents={metadata.get('total_agents', 0)}"
    )
    log(
        "Size metrics: "
        f"files={metadata.get('total_files', 0)} "
        f"tokens={metadata.get('total_estimated_tokens', 0)} "
        f"always_on={metadata.get('always_on_tokens', 0)}"
    )
    log(f"JSON report: {json_path.resolve()}")
    log(f"Markdown report: {markdown_path.resolve()}")


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    args = parse_args(sys.argv[1:] if argv is None else argv)
    payload: dict[str, object] = {}
    try:
        rootstock_repo = args.rootstock_repo.resolve()
        branch = str(args.branch).strip()
        if branch == "":
            raise ValueError("--branch cannot be blank.")

        ensure_directory(rootstock_repo, "--rootstock-repo")
        ensure_git_repository(rootstock_repo, args.verbose)
        if not branch_exists(rootstock_repo, branch, args.verbose):
            raise ValueError(f"Branch does not exist locally: {branch}")

        output_dir = resolve_output_dir(rootstock_repo, args.output_dir)
        cursor_files = list_cursor_files(rootstock_repo, branch, args.verbose)
        if not cursor_files:
            raise ValueError(f"No files found under {CURSOR_DIRNAME}/ on branch {branch}.")

        file_metrics = load_file_metrics(rootstock_repo, branch, cursor_files, args.verbose)
        skills = build_skill_maps(file_metrics)
        rules = build_rule_maps(file_metrics)
        agents = build_agent_maps(file_metrics)

        report = build_report(
            branch=branch,
            file_metrics=file_metrics,
            skills=skills,
            rules=rules,
            agents=agents,
        )
        json_path, markdown_path = write_reports(output_dir, report)
        print_human_summary(report, json_path, markdown_path)

        payload = report
        emit_json(payload)
        return EXIT_SUCCESS
    except Exception as exc:  # noqa: BLE001
        return fail(str(exc), payload if payload else None)


if __name__ == "__main__":
    raise SystemExit(main())
