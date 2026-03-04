# Semantic Number Ranges

Numbers encode precedence and scope. The always-on layer splits into universal (every context) and coding (software engineering contexts). Distribution filtering happens at the rootstock sync layer, not at rule activation.

## Overview

| Range | Activation | Purpose |
|-------|------------|---------|
| **000** | Always-on | Universal operating environment (intellectual safety, collaboration, agency) |
| **001-010** | Always-on | Coding process mandates (NASA, delegation mechanics, cascade tracing) |
| **011-099** | Description-activated | Universal non-always-on (environment, workflows, tooling) |
| **100-199** | Description + globs | Language-specific rules (Python, Rust, Java, TypeScript, Angular) |
| **200-999** | Varies | Project-specific (flexible organization) |

## Activation Strategy

Always include a `description` field alongside `globs` on any non-always-on rule. Glob activation is unreliable for agent-driven work (does not fire from agent Read tool calls; may only fire on editor-open files). The `description` field enables "Apply Intelligently" activation — the same mechanism skills use — as a reliable fallback.

## Range Details

### 000 (Universal Always-On)

`000-operating-environment` — intellectual safety, collaboration rhythm, agency, practice identity, universal disciplines. Travels to every environment via rootstock. Not coding-specific.

### 001-010 (Coding Always-On)

Coding process mandates. Always-on because planning and designing code requires these mandates in context even when no code files are open. Travels only to coding environments via rootstock sync policy.

### 011-099 (Universal Non-Always-On)

Environment, git workflows, documentation, planning, rule authoring. Reserved sub-range: **080-089** for universal UI patterns.

### 100-199 (Language-Specific)

Use `description` + `globs` for dual activation. Sub-ranges:

| Sub-Range | Language/Framework |
|-----------|-------------------|
| 100-109 | Python |
| 110-119 | Rust |
| 120-129 | Java |
| 130-139 | JavaScript/TypeScript core |
| 140-149 | Angular |
| 150-159 | SvelteKit (reserved) |
| 160-199 | Reserved |

### 200-999 (Project-Specific)

Flexible organization per project needs. No mandated sub-ranges.
