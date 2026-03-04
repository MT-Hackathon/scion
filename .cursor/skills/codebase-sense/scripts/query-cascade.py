#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = ["networkx>=3.0", "numpy>=1.26", "pyyaml>=6.0"]
# ///
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

# pyright: reportMissingImports=false
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib.cache as cache
from lib.helpers import as_int

MAX_FILES = 3
RISK_LEVELS = ((500, "CRITICAL"), (200, "HIGH"), (80, "MEDIUM"), (0, "LOW"))
SKILL_STOPWORDS = {"use", "when", "for", "the", "and", "with", "from", "this", "that", "any"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Query cached cascade intelligence for specific files."
    )
    parser.add_argument("files", nargs="+", help="1-3 file paths to analyze.")
    parser.add_argument(
        "--workspace",
        "-w",
        type=Path,
        default=None,
        help="Workspace root (default: auto-detect via .cursor).",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    args = parser.parse_args(argv)
    if len(args.files) > MAX_FILES:
        parser.error(f"accepts at most {MAX_FILES} files")
    return args


def detect_workspace(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.expanduser().resolve()
    current = Path.cwd().resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".cursor").is_dir():
            return candidate
    return current


def list_meta_keys(workspace_path: Path) -> list[str]:
    cache_path = cache.get_cache_path(workspace_path)
    if not cache_path.exists():
        return []
    try:
        with sqlite3.connect(cache_path) as connection:
            rows = connection.execute("SELECT key FROM scan_meta").fetchall()
    except sqlite3.Error:
        return []
    return sorted(str(row[0]) for row in rows if row and row[0])


def parse_json_meta(workspace_path: Path, keys: list[str]) -> dict[str, Any]:
    payloads: dict[str, Any] = {}
    for key in keys:
        try:
            raw = cache.load_meta(workspace_path, key)
            if not raw:
                continue
            payloads[key] = json.loads(raw)
        except Exception:
            continue
    return payloads


def cache_age_hours(workspace_path: Path) -> float | None:
    raw = cache.load_meta(workspace_path, "last_scan_epoch")
    if not raw:
        return None
    try:
        age_seconds = datetime.now(UTC).timestamp() - float(raw)
    except (TypeError, ValueError):
        return None
    return max(0.0, age_seconds / 3600.0)


def normalize_path_input(raw_path: str, workspace_path: Path) -> tuple[str, Path]:
    candidate = Path(raw_path).expanduser()
    absolute = candidate if candidate.is_absolute() else (workspace_path / candidate)
    resolved = absolute.resolve()
    try:
        relative = resolved.relative_to(workspace_path).as_posix()
    except ValueError:
        relative = candidate.as_posix().replace("\\", "/")
    return relative, resolved


def build_path_variants(relative_path: str, workspace_path: Path) -> set[str]:
    clean = relative_path.replace("\\", "/").lstrip("./")
    variants = {clean}
    parts = clean.split("/")
    if len(parts) > 1:
        variants.add("/".join(parts[1:]))
    variants.add(f"{workspace_path.name}/{clean}")
    return {item for item in variants if item}


def path_matches(candidate: str, variants: set[str]) -> bool:
    normalized = candidate.replace("\\", "/").strip()
    if not normalized:
        return False
    for variant in variants:
        if normalized == variant or normalized.endswith(f"/{variant}"):
            return True
    return False


def collect_structural(payloads: dict[str, Any], variants: set[str]) -> dict[str, list[str]]:
    imports: set[str] = set()
    imported_by: set[str] = set()
    for key, payload in payloads.items():
        if "structural_graph_edges" not in key and "graph_edges" not in key:
            continue
        if not isinstance(payload, list):
            continue
        for edge in payload:
            if not isinstance(edge, list) or len(edge) != 2:
                continue
            source = str(edge[0])
            target = str(edge[1])
            if path_matches(source, variants):
                imports.add(target)
            if path_matches(target, variants):
                imported_by.add(source)
    return {
        "imports": sorted(imports),
        "imported_by": sorted(imported_by),
    }


def collect_risk(payloads: dict[str, Any], variants: set[str]) -> dict[str, Any] | None:
    for key, payload in payloads.items():
        if "risk" not in key and "hotspot" not in key and "complexity" not in key:
            continue
        if not isinstance(payload, list):
            continue
        for item in payload:
            if not isinstance(item, dict):
                continue
            raw_path = item.get("path")
            if not isinstance(raw_path, str) or not path_matches(raw_path, variants):
                continue
            complexity = as_int(item.get("max_cyclomatic"), 0)
            churn = as_int(item.get("churn_30d"), 0)
            risk_product = as_int(item.get("risk_product"), complexity * churn)
            return {
                "source": key,
                "complexity": complexity,
                "churn": churn,
                "risk_product": risk_product,
                "level": risk_level(risk_product),
            }
    return None


def collect_cochange(payloads: dict[str, Any], variants: set[str]) -> list[dict[str, Any]]:
    predictions: list[dict[str, Any]] = []
    for key, payload in payloads.items():
        if "cascade" not in key and "cochange" not in key and "behavioral" not in key:
            continue
        if not isinstance(payload, list):
            continue
        for item in payload:
            if not isinstance(item, dict):
                continue
            trigger = item.get("trigger")
            targets = item.get("targets")
            if not isinstance(trigger, str) or not path_matches(trigger, variants):
                continue
            if not isinstance(targets, list):
                continue
            for target in targets:
                if not isinstance(target, (list, tuple)) or len(target) < 2:
                    continue
                target_path = str(target[0])
                confidence = float(target[1])
                predictions.append(
                    {
                        "path": target_path,
                        "confidence": max(0.0, min(1.0, confidence)),
                        "co_occurrences": None,
                        "source": key,
                    }
                )
    predictions.sort(key=lambda item: item["confidence"], reverse=True)
    return predictions[:5]


def collect_test_files(payloads: dict[str, Any], variants: set[str]) -> list[str]:
    discovered: set[str] = set()
    for key, payload in payloads.items():
        lowered = key.lower()
        if "test" not in lowered and "mapping" not in lowered and "map" not in lowered:
            continue
        if isinstance(payload, dict):
            for source, record in payload.items():
                if not isinstance(source, str) or not path_matches(source, variants):
                    continue
                if isinstance(record, dict):
                    for path in record.get("test_paths", []):
                        if isinstance(path, str):
                            discovered.add(path)
        if isinstance(payload, list):
            for record in payload:
                if not isinstance(record, dict):
                    continue
                source = record.get("source_path") or record.get("path")
                if not isinstance(source, str) or not path_matches(source, variants):
                    continue
                test_paths = record.get("test_paths")
                if isinstance(test_paths, list):
                    for path in test_paths:
                        if isinstance(path, str):
                            discovered.add(path)
    return sorted(discovered)


def load_skills(workspace_path: Path) -> list[dict[str, str]]:
    skills_dir = workspace_path / ".cursor" / "skills"
    if not skills_dir.is_dir():
        return []
    skills: list[dict[str, str]] = []
    for skill_dir in sorted(skills_dir.iterdir()):
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue
        try:
            text = skill_file.read_text(encoding="utf-8")
        except OSError:
            continue
        if not text.startswith("---"):
            continue
        try:
            end_index = text.index("---", 3)
        except ValueError:
            continue
        try:
            frontmatter = yaml.safe_load(text[3:end_index]) or {}
        except yaml.YAMLError:
            continue
        name = str(frontmatter.get("name") or skill_dir.name).strip()
        description = str(frontmatter.get("description") or "").strip()
        skills.append({"name": name, "description": description, "dir": skill_dir.name})
    return skills


def match_governing_skills(relative_path: str, skills: list[dict[str, str]]) -> list[dict[str, str]]:
    normalized = relative_path.lower().replace("\\", "/")
    path_tokens = {
        part
        for part in normalized.replace(".", "/").split("/")
        if part and len(part) >= 4 and part not in {"cursor", "hooks", "skills", "rules", "script", "scripts"}
    }
    scored: list[tuple[int, dict[str, str]]] = []
    for skill in skills:
        skill_name = skill["name"].lower()
        direct_match = normalized.startswith(f".cursor/skills/{skill['dir'].lower()}/")
        description_tokens = {
            token.strip(".,()")
            for token in skill["description"].lower().split()
            if token and token.strip(".,()") not in SKILL_STOPWORDS
        }
        overlap = len(path_tokens.intersection(description_tokens))
        score = overlap + (100 if direct_match else 0) + (5 if skill_name in path_tokens else 0)
        if score >= 2 or direct_match:
            scored.append((score, skill))
    scored.sort(key=lambda item: (-item[0], item[1]["name"]))
    return [skill for _, skill in scored[:4]]


def risk_level(risk_product: int) -> str:
    for threshold, label in RISK_LEVELS:
        if risk_product >= threshold:
            return label
    return "LOW"


def render_text(result: dict[str, Any]) -> str:
    lines: list[str] = []
    for entry in result["files"]:
        lines.append(f"Cascade Analysis for: {entry['path']}")
        lines.append("==========================================")
        lines.append(f"Cache: {result['cache_status_line']}")
        lines.append("")
        risk = entry.get("risk")
        if risk:
            lines.append(
                f"Risk: {risk['level']} (complexity={risk['complexity']}, churn={risk['churn']}, "
                f"risk_product={risk['risk_product']})"
            )
        else:
            lines.append("Risk: unavailable (no matching risk data in cache)")
        lines.append("")
        lines.append("Co-Change Predictions:")
        if entry["cochange"]:
            for item in entry["cochange"]:
                confidence_pct = round(item["confidence"] * 100)
                co_occurrences = item["co_occurrences"]
                evidence = f", {co_occurrences} co-occurrences" if co_occurrences is not None else ""
                lines.append(f"  -> {item['path']} ({confidence_pct}% confidence{evidence})")
        else:
            lines.append("  (no co-change data for this file)")
        lines.append("")
        lines.append("Structural Dependencies:")
        imports = ", ".join(entry["structural"]["imports"]) or "(none)"
        imported_by = ", ".join(entry["structural"]["imported_by"]) or "(none)"
        lines.append(f"  imports: {imports}")
        lines.append(f"  imported_by: {imported_by}")
        lines.append("")
        lines.append("Test Coverage:")
        if entry["test_files"]:
            for test_path in entry["test_files"]:
                lines.append(f"  -> {test_path}")
        else:
            lines.append("  (no test mapping data for this file)")
        lines.append("")
        lines.append("Governing Skills:")
        if entry["skills"]:
            for skill in entry["skills"]:
                lines.append(f"  -> {skill['name']} ({skill['description']})")
        else:
            lines.append("  (no clear skill match)")
        lines.append("")
        recommended = ", ".join(entry["recommended_wfs"]) or entry["path"]
        lines.append(f"Recommended WFS:\n  {recommended}")
        if entry["notes"]:
            lines.append("")
            for note in entry["notes"]:
                lines.append(f"Note: {note}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    workspace_path = detect_workspace(args.workspace)
    cache_path = cache.get_cache_path(workspace_path)
    if not cache_path.exists():
        message = "No codebase-sense cache found. Run briefing.py first."
        if args.format == "json":
            print(json.dumps({"error": message}, indent=2))
        else:
            print(message)
        return 1

    is_fresh = cache.is_cache_fresh(workspace_path)
    age_hours = cache_age_hours(workspace_path)
    if age_hours is None:
        cache_status_line = "unknown age (missing timestamp)"
    else:
        cache_status_templates = {
            True: "fresh ({age:.1f} hours old)",
            False: "stale ({age:.1f} hours old, re-run briefing for accuracy)",
        }
        cache_status_line = cache_status_templates[is_fresh].format(age=age_hours)

    all_keys = list_meta_keys(workspace_path)
    payloads = parse_json_meta(workspace_path, all_keys)
    skills = load_skills(workspace_path)

    files_out: list[dict[str, Any]] = []
    for raw_path in args.files:
        relative_path, resolved_path = normalize_path_input(raw_path, workspace_path)
        variants = build_path_variants(relative_path, workspace_path)
        notes: list[str] = []

        risk_data = collect_risk(payloads, variants)
        cochange = collect_cochange(payloads, variants)
        structural_data = collect_structural(payloads, variants)
        test_files = collect_test_files(payloads, variants)
        matched_skills = match_governing_skills(relative_path, skills)

        if not risk_data and not cochange and not structural_data["imports"] and not structural_data["imported_by"]:
            notes.append("File not found in cached analysis. It may be new or excluded.")
        if not test_files:
            notes.append("Test mapping data missing or unmatched.")
        recommended_set = {
            relative_path,
            *(item["path"] for item in cochange[:2]),
            *structural_data["imports"][:2],
            *structural_data["imported_by"][:2],
            *test_files[:2],
        }
        recommended_wfs = sorted(path for path in recommended_set if path)

        files_out.append(
            {
                "path": relative_path,
                "resolved": str(resolved_path),
                "risk": risk_data,
                "cochange": cochange,
                "structural": structural_data,
                "test_files": test_files,
                "skills": matched_skills,
                "recommended_wfs": recommended_wfs,
                "notes": notes,
            }
        )

    result = {
        "workspace": str(workspace_path),
        "cache_path": str(cache_path),
        "cache_fresh": is_fresh,
        "cache_age_hours": age_hours,
        "cache_status_line": cache_status_line,
        "available_meta_keys": all_keys,
        "files": files_out,
    }

    formatters = {
        "json": lambda payload: print(json.dumps(payload, indent=2)),
        "text": lambda payload: print(render_text(payload), end=""),
    }
    formatter = formatters.get(args.format, formatters["text"])
    formatter(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
