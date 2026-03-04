#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Accessibility smoke test using axe-core with graceful fallbacks.
"""

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from typing import Dict, List, Optional

DEFAULT_BASE_URL = "http://localhost:4200"
DEFAULT_ROUTES = ["/", "/login", "/dashboard"]
AXE_CDN = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js"
IMPACT_ORDER = ["critical", "serious", "moderate", "minor", "unknown"]
WCAG_TAGS = {
    "A": ["wcag2a", "wcag21a"],
    "AA": ["wcag2aa", "wcag21aa"],
    "AAA": ["wcag2aaa", "wcag21aaa"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run axe-core accessibility audit against Angular routes.",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Base URL to test (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--routes",
        default=",".join(DEFAULT_ROUTES),
        help="Comma-separated routes to test (default: /,/login,/dashboard)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output file for report (default: stdout)",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format (default: markdown)",
    )
    parser.add_argument(
        "--level",
        choices=["A", "AA", "AAA"],
        default="AA",
        help="WCAG conformance level (default: AA)",
    )
    return parser.parse_args()


def split_routes(value: str) -> List[str]:
    return [route.strip() or "/" for route in value.split(",")]


def detect_runner() -> str:
    try:
        import playwright  # noqa: F401

        return "playwright"
    except ImportError:
        if shutil.which("pa11y"):
            return "pa11y"
    return "static"


def fetch_axe_source() -> Optional[str]:
    try:
        with urllib.request.urlopen(AXE_CDN, timeout=10) as response:
            return response.read().decode("utf-8")
    except Exception:
        return None


def inject_axe(page) -> None:
    # Try CDN first, fall back to in-memory source.
    try:
        page.add_script_tag(url=AXE_CDN)
        return
    except Exception:
        axe_source = fetch_axe_source()
        if axe_source:
            page.add_script_tag(content=axe_source)
            return
    raise RuntimeError("axe-core not available. Ensure network access or install axe-core locally.")


def run_playwright(base_url: str, routes: List[str], level: str) -> List[Dict]:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright

    results: List[Dict] = []
    tags = WCAG_TAGS.get(level, WCAG_TAGS["AA"])

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            for route in routes:
                url = base_url.rstrip("/") + route
                route_result = {"route": route, "violations": [], "error": None}
                try:
                    page.goto(url, wait_until="networkidle", timeout=20000)
                    inject_axe(page)
                    violations = page.evaluate(
                        """async (runTags) => {
                            if (!window.axe) throw new Error('axe failed to load');
                            const options = { runOnly: { type: 'tag', values: runTags }, resultTypes: ['violations'] };
                            const report = await axe.run(document, options);
                            return report.violations;
                        }""",
                        tags,
                    )
                    for item in violations:
                        route_result["violations"].append(
                            {
                                "rule": item.get("id", "unknown"),
                                "impact": (item.get("impact") or "unknown").lower(),
                                "description": item.get("help", item.get("description", "")),
                                "nodes": [
                                    ", ".join(node.get("target", [])) or "element"
                                    for node in item.get("nodes", [])
                                ],
                            }
                        )
                except PlaywrightTimeoutError:
                    route_result["error"] = f"Timed out loading {url}"
                except Exception as exc:  # pragma: no cover - defensive
                    route_result["error"] = f"{type(exc).__name__}: {exc}"
                results.append(route_result)
        finally:
            browser.close()
    return results


def wcag_standard(level: str) -> str:
    return {"A": "WCAG2A", "AA": "WCAG2AA", "AAA": "WCAG2AAA"}.get(level, "WCAG2AA")


def run_pa11y(base_url: str, routes: List[str], level: str) -> List[Dict]:
    results: List[Dict] = []
    standard = wcag_standard(level)
    for route in routes:
        url = base_url.rstrip("/") + route
        route_result = {"route": route, "violations": [], "error": None}
        try:
            proc = subprocess.run(
                ["pa11y", url, "--reporter", "json", "--standard", standard],
                check=False,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if proc.returncode not in (0, 2):
                raise RuntimeError(proc.stderr.strip() or "pa11y execution failed")
            issues = json.loads(proc.stdout or "[]")
            for issue in issues:
                impact = {
                    "error": "serious",
                    "warning": "moderate",
                    "notice": "minor",
                }.get(issue.get("type", "").lower(), "unknown")
                route_result["violations"].append(
                    {
                        "rule": issue.get("code", "pa11y"),
                        "impact": impact,
                        "description": issue.get("message", ""),
                        "nodes": [issue.get("selector", "element")],
                    }
                )
        except Exception as exc:  # pragma: no cover - defensive
            route_result["error"] = f"{type(exc).__name__}: {exc}"
        results.append(route_result)
    return results


def run_static_checks(base_url: str, routes: List[str]) -> List[Dict]:
    results: List[Dict] = []
    for route in routes:
        url = base_url.rstrip("/") + route
        route_result = {"route": route, "violations": [], "error": None}
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                html = response.read().decode("utf-8", errors="ignore")
            checks = static_heuristics(html)
            route_result["violations"].extend(checks)
        except urllib.error.HTTPError as exc:
            route_result["error"] = f"HTTP {exc.code} for {url}"
        except Exception as exc:  # pragma: no cover - defensive
            route_result["error"] = f"{type(exc).__name__}: {exc}"
        results.append(route_result)
    return results


def static_heuristics(html: str) -> List[Dict]:
    violations: List[Dict] = []
    lower_html = html.lower()

    if "<title>" not in lower_html or "</title>" not in lower_html:
        violations.append(
            {
                "rule": "document-title",
                "impact": "moderate",
                "description": "Document is missing a <title> element.",
                "nodes": ["<head>"],
            }
        )

    if not re.search(r"<html[^>]*lang=", lower_html):
        violations.append(
            {
                "rule": "html-has-lang",
                "impact": "moderate",
                "description": "<html> element is missing a lang attribute.",
                "nodes": ["<html>"],
            }
        )

    img_tags = re.findall(r"<img [^>]*>", lower_html)
    for tag in img_tags:
        if "alt=" not in tag:
            violations.append(
                {
                    "rule": "image-alt",
                    "impact": "minor",
                    "description": "Image is missing an alt attribute.",
                    "nodes": [tag[:60] + ("..." if len(tag) > 60 else "")],
                }
            )

    if re.search(r'<form[^>]*>(?!.*<\/label>)', lower_html, flags=re.DOTALL):
        violations.append(
            {
                "rule": "form-labels",
                "impact": "moderate",
                "description": "Forms should include visible labels for inputs.",
                "nodes": ["<form>"],
            }
        )

    return violations


def summarize(results: List[Dict]) -> Dict:
    summary = {
        "routes_tested": len(results),
        "total_violations": 0,
        "by_impact": {impact: 0 for impact in IMPACT_ORDER},
        "error_routes": 0,
    }
    for result in results:
        if result.get("error"):
            summary["error_routes"] += 1
            continue
        summary["total_violations"] += len(result.get("violations", []))
        for violation in result.get("violations", []):
            impact = violation.get("impact", "unknown")
            summary["by_impact"][impact] = summary["by_impact"].get(impact, 0) + 1
    return summary


def render_markdown(results: List[Dict], summary: Dict, base_url: str, level: str) -> str:
    lines: List[str] = []
    lines.append("# Accessibility Audit Report\n")
    lines.append(f"**Date:** {datetime.date.today().isoformat()}")
    lines.append(f"**Base URL:** {base_url}")
    lines.append(f"**WCAG Level:** {level}\n")

    lines.append("## Summary")
    lines.append(f"- Routes tested: {summary['routes_tested']}")
    lines.append(f"- Total violations: {summary['total_violations']}")
    lines.append(f"- Critical: {summary['by_impact'].get('critical', 0)}")
    lines.append(f"- Serious: {summary['by_impact'].get('serious', 0)}")
    lines.append(f"- Moderate: {summary['by_impact'].get('moderate', 0)}")
    lines.append(f"- Minor: {summary['by_impact'].get('minor', 0)}")
    lines.append(f"- Routes with errors: {summary.get('error_routes', 0)}\n")

    lines.append("## Violations by Route\n")
    for result in results:
        lines.append(f"### {result['route']}")
        if result.get("error"):
            lines.append(f"Error: {result['error']}\n")
            continue
        if not result.get("violations"):
            lines.append("No violations found.\n")
            continue
        lines.append("| Rule | Impact | Description | Elements |")
        lines.append("|------|--------|-------------|----------|")
        for violation in result["violations"]:
            nodes = "<br>".join(violation.get("nodes") or ["element"])
            lines.append(
                f"| {violation.get('rule')} | {violation.get('impact')} | "
                f"{violation.get('description')} | {nodes} |"
            )
        lines.append("")  # blank line after table
    return "\n".join(lines).strip() + "\n"


def render_json(results: List[Dict], summary: Dict, base_url: str, level: str) -> str:
    payload = {
        "date": datetime.date.today().isoformat(),
        "base_url": base_url,
        "level": level,
        "summary": summary,
        "routes": results,
    }
    return json.dumps(payload, indent=2)


def write_output(content: str, output_path: Optional[str]) -> None:
    if not output_path:
        sys.stdout.write(content)
        return
    parent = os.path.dirname(output_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write(content)


def main() -> int:
    args = parse_args()
    base_url = args.base_url.rstrip("/")
    routes = split_routes(args.routes) or DEFAULT_ROUTES
    level = args.level.upper()

    runner = detect_runner()
    results: List[Dict]

    if runner == "playwright":
        results = run_playwright(base_url, routes, level)
    elif runner == "pa11y":
        results = run_pa11y(base_url, routes, level)
    else:
        results = run_static_checks(base_url, routes)

    summary = summarize(results)
    if args.format == "json":
        output = render_json(results, summary, base_url, level)
    else:
        output = render_markdown(results, summary, base_url, level)

    write_output(output, args.output)
    if runner == "static":
        sys.stderr.write(
            "INFO: Falling back to static HTML heuristics. Install playwright (pip install playwright && playwright install chromium) "
            "or pa11y for full axe-core coverage.\n"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
