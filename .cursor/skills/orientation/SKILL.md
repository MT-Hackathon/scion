---
name: orientation
description: "Provides a script and tool catalog across all skills for navigation and discovery. Use when searching for which skill has the script you need, auditing available automation, or running session-start environment health checks. DO NOT use for skill content itself — navigate to the relevant skill directly once located."
---

<ANCHORSKILL-ORIENTATION>

# Orientation & Discovery

Teaches the AI assistant how to orient itself at the start of a session and catalogs scripts available for environment awareness.

## Table of Contents
- [1. The Warmup Pattern](#1-the-warmup-pattern)
- [2. Script Catalog](#2-script-catalog)
  - [Environment Status](#environment-status)
  - [Schema & Database](#schema--database)
  - [Contract & API](#contract--api)
  - [Code Quality](#code-quality)
  - [Pre-Dispatch Intelligence](#pre-dispatch-intelligence)
  - [Delegation Analysis](#delegation-analysis)
  - [Knowledge Analysis](#knowledge-analysis)
  - [Diagramming](#diagramming)
- [3. When to Use Each](#3-when-to-use-each)
- [4. Cross-References](#4-cross-references)

## 1. The Warmup Pattern

Elite AI-assisted development begins with a deliberate "warmup" routine to ensure the assistant has the correct mental model of the current state.

1.  **Clean Slate**: Start fresh or clear context to avoid carrying over irrelevant information from previous unrelated tasks.
2.  **Orientation Prompt**: Ask the assistant to "summarize recent changes" and "what is the current state of the feature/branch?"
3.  **Environment Sync**: Run discovery scripts to check what's running and what's changed in the environment.

## 2. Script Catalog

These scripts are organized by purpose to help you quickly understand the system state.

### Environment Status
Used to verify that the local development environment is healthy and all necessary services are reachable.

- **`uv run dev-stack.py status`**: Check running services, ports, and health.
  - **Arguments**:
    - `--format [json|markdown|text]`: Set output format (default: markdown)
    - `--check-health`: Perform active health checks on services
    - `--ports`: List active ports and listeners

### Schema & Database
Used to understand the data model and ensure the application matches the database state.

- **`uv run schema-summary.py`**: Generate Mermaid ERD from JPA entities.
  - **Arguments**:
    - `--format [mermaid|text]`: Set output format
- **`uv run schema-diff.py`**: Compare JPA entity definitions to the live database schema.
- **`uv run seed-data.py`**: Generate test data for development and testing.

### Contract & API
Used to manage and test API definitions from the unified code-first source (backend DTO records + Springdoc annotations, exported via `/v3/api-docs`).

- **`uv run mock-server.py`**: Boot a Prism mock server from an OpenAPI specification.
  - **Arguments**:
    - `--spec`: Path to the OpenAPI spec file
    - `--port`: Port to run the mock server on
    - `--dynamic`: Enable dynamic response generation
    - `--stop`: Stop the running mock server

### Code Quality
Used to audit the application for compliance with standards.

- **`uv run a11y-smoke.py`**: Run an accessibility audit on specified routes.
  - **Arguments**:
    - `--base-url`: The root URL to audit
    - `--routes`: Comma-separated list of routes
    - `--format`: Output format (json/markdown)
    - `--level`: WCAG level (A/AA/AAA)
    - `--output`: File path for the report
- **`uv run find-todos.py`**: Find TODOs and FIXMEs across the codebase.
- **`uv run find-linter-patterns.py`**: Analyze linter results for recurring patterns.

### Pre-Dispatch Intelligence
Used before delegating to an executor to understand cascade risk for files that will be touched.

- **`uv run .cursor/skills/codebase-sense/scripts/query-cascade.py <file1> [file2...] [--workspace path] [--format text|json]`**: Fast cache lookup returning risk scores, co-change predictions, structural dependencies, and governing skills for specified files.

### Delegation Analysis
Used to retrospect on delegation quality and identify brief patterns that correlate with rework.

- **`uv run .cursor/skills/conversation-history/scripts/delegation-retro.py [--project path] [--sessions N] [--format text|json]`**: Analyze past delegations for brief quality signals, agent type success rates, and rework triggers.

### Knowledge Analysis
Used to build and inspect knowledge links across skills and rules.

- **`uv run .cursor/skills/orientation/scripts/build-knowledge-graph.py`**: Build and analyze the knowledge graph of skill/rule cross-references.
  - **Arguments**:
    - `--cursor-dir path`: Path to `.cursor` directory
    - `--format text|mermaid|json`: Output format
    - `--include-rules`: Include rule nodes and rule-to-skill links

### Diagramming
Used to generate Mermaid diagrams, render to images, and bundle for sharing.

- **`uv run diagram.py render`**: Generate `.mmd` source and optionally render to SVG/PNG.
  - **Arguments**:
    - `--input <file>` / `--text "<mermaid>"` / stdin: Mermaid source (exactly one)
    - `--name <slug>`: Required kebab-case diagram name
    - `--format [svg|png]`: Image format (default: svg)
    - `--profile [assistant|shareable]`: Output location
    - `--dry-run`: Preview without writing
- **`uv run diagram.py bundle`**: Create markdown wrapper with Mermaid source block for committing.
  - **Arguments**: Same input/name/profile as render, plus `--title` and `--description`
- **`uv run diagram.py check`**: Detect local renderers and provide setup guidance.

## 3. When to Use Each

| Trigger | Recommended Action |
| :--- | :--- |
| **Session Start** | Run `uv run dev-stack.py status` |
| **Before Implementation** | Run `uv run schema-summary.py` to visualize the domain model |
| **Before PR / Merge** | Run `uv run a11y-smoke.py` to ensure no accessibility regressions |
| **Debugging / Issues** | Run `uv run dev-stack.py status --check-health` to rule out environment failures |
| **Architecture / Documentation** | Run `uv run diagram.py render` or `bundle` to create committed diagrams |

## 4. Cross-References

- [git-workflows](../git-workflows/SKILL.md) — managing branch state and PR submission
- [dev-project-architecture](../dev-project-architecture/SKILL.md) — unified workspace structure and cross-repo coordination
- [postgresql-design](../postgresql-design/SKILL.md) — deep dives into database patterns
- [accessibility](../accessibility/SKILL.md) — detailed WCAG/Section 508 requirements
- [diagramming](../diagramming/SKILL.md) — Mermaid diagram generation, rendering, and Lucidchart portability

</ANCHORSKILL-ORIENTATION>