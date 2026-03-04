---
name: diagramming
description: "Governs Mermaid diagram creation, rendering, and distribution for committed visual artifacts. Use when creating architecture diagrams, data flows, sequence diagrams, ER diagrams, or any diagram committed to the repo. Provides local-only rendering (no network), placement profiles, and Lucidchart portability. Portable to any project. DO NOT use for data visualizations generated from code (charts/plots), UI mockups, or documentation prose (see documentation-lifecycle)."
---

<ANCHORSKILL-DIAGRAMMING>

# Diagramming

Local Mermaid diagram generation with source management, optional image rendering, and documented Lucidchart portability. Portable to any project -- pure Python stdlib, no ecosystem-specific dependencies.

## Table of Contents

- [Core Concepts](#core-concepts)
- [Quick Start](#quick-start)
- [Script Reference](#script-reference)
- [Templates](#templates)
- [Lucidchart Bridge](#lucidchart-bridge)
- [Governance](#governance)
- [Resources](#resources)

## Core Concepts

- **Mermaid source is truth**. Images are derived artifacts. The `.mmd` file is always created; rendering is optional.
- **Zero data egress**. All rendering is local. No Kroki, no mermaid.ink, no external APIs.
- **Detect-and-use rendering**. The script detects `mmdc` (Node) or `playwright` (Python) at runtime. Neither required. Source-only output is a valid success.
- **Placement profiles**. `assistant` (`.cursor/docs/diagrams/`) for working drafts, `shareable` (`docs/diagrams/`) for committed artifacts.
- **GitLab/GitHub render natively**. Markdown files with ` ```mermaid ` blocks render without tooling.
- **Lucidchart imports Mermaid directly**. Paste source into "Diagram as Code" panel.

## Quick Start

Generate and save a diagram:

```bash
uv run .cursor/skills/diagramming/scripts/diagram.py render --text "graph LR; A-->B; B-->C" --name quick-sketch
```

Bundle for committing to the repo:

```bash
uv run .cursor/skills/diagramming/scripts/diagram.py bundle --input my-diagram.mmd --profile shareable --name api-flow --title "API Data Flow"
```

Check local rendering capability:

```bash
uv run .cursor/skills/diagramming/scripts/diagram.py check
```

## Script Reference

All commands: `uv run .cursor/skills/diagramming/scripts/diagram.py <command> [args]`

### diagram.py render

Mermaid source to `.mmd` file, plus image (SVG/PNG) if renderer available.

| Arg | Purpose |
|-----|---------|
| `--input <file>` | Read Mermaid from file |
| `--text "<mermaid>"` | Inline Mermaid source |
| (stdin) | Pipe Mermaid source |
| `--name <slug>` | Required. Kebab-case diagram name |
| `--format svg\|png` | Image format (default: svg) |
| `--profile assistant\|shareable` | Output location (default: assistant) |
| `--output-dir <path>` | Explicit output directory override |
| `--dry-run` | Preview without writing files |

Exactly one input source required (`--input`, `--text`, or stdin).

### diagram.py bundle

Mermaid source to markdown wrapper for committing. Creates both `.mmd` and `.md` files.

| Arg | Purpose |
|-----|---------|
| `--input <file>` | Read Mermaid from file |
| `--text "<mermaid>"` | Inline Mermaid source |
| (stdin) | Pipe Mermaid source |
| `--name <slug>` | Required. Kebab-case diagram name |
| `--title <text>` | Human-readable title (defaults to humanized name) |
| `--description <text>` | Optional description for metadata |
| `--profile assistant\|shareable` | Output location (default: assistant) |
| `--output-dir <path>` | Explicit output directory override |
| `--dry-run` | Preview without writing files |

### diagram.py check

Detect OS, report available renderers, provide install suggestions. Generates `puppeteerConfig.json` if mmdc is found but config is missing.

No arguments.

## Templates

Starter templates in `resources/templates/`. Use as a base -- fill in placeholders, adapt to the domain.

| Template | Diagram Type | Use For |
|----------|-------------|---------|
| `architecture-overview.mmd` | Flowchart | Module/service relationships |
| `data-flow.mmd` | Flowchart | Request lifecycle through layers |
| `sequence-api.mmd` | Sequence | API call with auth, service, DB |
| `er-diagram.mmd` | ER | Entity relationships |
| `c4-context.mmd` | Flowchart (C4) | System boundaries, actors, integrations |

Domain-specific templates can be added in `resources/templates/domain/`.

## Lucidchart Bridge

The state uses Lucidchart/Lucidspark. Mermaid source is the portable artifact.

**Into Lucidchart**: Open Lucidchart > Insert menu > "Diagram as Code" panel > paste `.mmd` contents. Lucid generates editable shapes.

**Out of Lucidchart**: Export as PNG/SVG, place in `docs/diagrams/`. Write a corresponding `.mmd` source as the versioned truth.

**Principle**: Lucid versions are presentation copies. The `.mmd` in the repo is the system of record.

See [guide-lucidchart-bridge.md](resources/guide-lucidchart-bridge.md) for detailed walkthrough.

## Governance

### Audience-First Ordering
Order diagram suites for progressive disclosure:
- Start with business truth (system context, domain lifecycle) before technical internals.
- Include a "Quick Start by Audience" index to guide readers to relevant entry points.

### Diagram Metadata
Every committed `.mmd` file must include these governance comments:
- `%% Audience: <targeted_persona>` (e.g., Architect, Developer, Business Stakeholder)
- `%% Last verified: YYYY-MM-DD` (Date last checked against source code/system)
- `%% Source of truth: <file_or_system_path>` (Where the authoritative logic lives)

### Source-to-Diagram Mapping
Maintain a project-specific mapping of source files to diagrams so changes trigger the right verification. Store the mapping in a `resources/source-to-diagram.md` within the project's own docs.

Generic pattern:

| Source File Pattern | Diagram(s) to Verify |
|---|---|
| Domain model files (e.g., status enums, core entities) | `request-lifecycle.mmd`, `data-model-*.mmd` |
| API/controller entry points, routing config | `architecture-overview.mmd` |
| Security/auth pipeline files | `identity-security-flow.mmd`, `architecture-overview.mmd` |
| Frontend interceptors, HTTP client configuration | `identity-security-flow.mmd` |

After completing an edit to mapped source files, verify the corresponding diagram(s). If a diagram is updated, refresh the `%% Last verified:` date. If the change does not alter diagrammed behavior, no diagram update is required.

### Drift Prevention
- **Update Triggers**: Identify what code changes make the diagram stale.
- **Automated Reminders**: Use the source-to-diagram mapping table in this skill as the reminder trigger when source-of-truth files are edited.
- **Code Review**: Keep source files in `docs/diagrams/` (shareable profile) to ensure diagram changes are visible in PR diffs.

## Resources

- [Mermaid Patterns Reference](resources/reference-mermaid-patterns.md) -- syntax quick-reference for common diagram types
- [Lucidchart Bridge Guide](resources/guide-lucidchart-bridge.md) -- detailed import/export walkthrough

## Cross-References

- [documentation-lifecycle](../documentation-lifecycle/SKILL.md) — governs placement, naming, and lifecycle for committed docs and test artifacts

</ANCHORSKILL-DIAGRAMMING>
