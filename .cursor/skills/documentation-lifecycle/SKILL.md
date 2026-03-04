---
name: documentation-lifecycle
description: "Governs documentation placement, naming, and lifecycle for test reports, implementation docs, and planning artifacts. Use when creating test reports, implementation summaries, or organizing complex work artifacts to prevent root directory clutter. DO NOT use for application code inline comments or skill/rule authoring (see skill-authoring-patterns)."
---

<ANCHORSKILL-DOC-LIFECYCLE>

# Documentation Lifecycle

## Table of Contents & Resources

- [Core Concepts](#core-concepts)
- [Examples: Doc Organization](resources/examples-doc-organization.md)
- [Checklist: Doc Creation](resources/checklist-doc-creation.md)
- [Cross-References](resources/cross-references.md)

## Core Concepts

- **Anti-Root Clutter**: NEVER add documentation files to the project root.
- **Standardized Locations**:
  - **Plans**: `.cursor/plans/` — feature implementations, refactoring specs
  - **Test Reports**: `docs/test-reports/` — pytest/integration results with `YYYY-MM-DD-` prefix
  - **Implementation Docs**: `docs/implementations/` — architecture decisions, API redesigns
  - **ADRs**: `docs/adr/` — numbered decisions (`0001-use-polars-for-ecs.md`)
- **Pruning**: Archive completed plans quarterly; delete stale test reports after 90 days.
- **Naming**: Use kebab-case. Include `YYYY-MM-DD-` prefix for time-sensitive documents.

### Universal-API Document Types

| Type | Location | Naming | Example |
|------|----------|--------|---------|
| Pipeline config specs | `docs/implementations/` | `pipeline-{name}.md` | `pipeline-weather-api.md` |
| API version docs | `docs/implementations/` | `api-v{n}-changes.md` | `api-v2-changes.md` |
| ECS architecture | `docs/adr/` | `{nnnn}-{topic}.md` | `0002-dataframe-storage.md` |
| Cursor rules | `.cursor/rules/` | See rule-authoring-patterns skill | — |

## Script Reference

### filter_sast_report.py
Filters GitLab SAST (Semgrep) reports to produce actionable summaries.

`uv run filter_sast_report.py [input] [--output-dir <path>] [--format json|md|both] [--quiet]`

| Arg | Purpose |
|-----|---------|
| `[input]` | Path to SAST report JSON (default: .cursor/docs/gl-sast-report.json) |
| `--output-dir` | Output directory (default: .cursor/docs) |
| `--format` | Output format (json, md, both) (default: both) |
| `--quiet` | Suppress console output |

### render-report.py
Render structured JSON analysis data to HTML or XLSX for stakeholder-ready output.

`uv run .cursor/skills/documentation-lifecycle/scripts/render-report.py [input.json] [--format html|xlsx] [--output path] [--title "Override Title"]`

| Arg | Purpose |
|-----|---------|
| `input.json` | JSON input file (or reads from stdin) |
| `--format` | Output format: `html` (default) or `xlsx` |
| `--output` | Output file path (auto-generated if omitted) |
| `--title` | Override the title from JSON input |


</ANCHORSKILL-DOC-LIFECYCLE>
