---
name: ui-canvas
description: "Governs SvelteFlow canvas and pipeline patterns: node types, edge validation, configuration save/load, and pipeline persistence. Use when working with the pipeline canvas, node styling, or persisting pipeline configurations. DO NOT use for general Svelte component/form patterns (see svelte-ui)."
---

<ANCHORSKILL-UI-CANVAS>

# UI Canvas

## Table of Contents & Resources
- [Core Concepts](#core-concepts)
- [Blueprint: Canvas Node](blueprints/canvas-node.svelte)
- [Reference: Node Types](resources/reference-node-types.md)
- [Reference: Edge Validation](resources/reference-edge-validation.md)
- [Examples: Config Persistence](resources/examples-config-persistence.md)
- [Checklist: Node Creation](resources/checklist-node-creation.md)
- [Checklist: Config Save/Load](resources/checklist-config-save-load.md)
- [Cross-References](#cross-references) | [Full detail](resources/cross-references.md)

## Core Concepts

### Canvas & Node Types
SvelteFlow or SVG; **API Source** (Green): out-only; **Database Target** (Blue): in-only; **Transform** (Purple/Amber): bidirectional

Node fill/border/text colors must come from the token system described in `.cursor/skills/svelte-ui/SKILL.md` to keep the saturated theme consistent.

### Edge Validation
**Allowed:** API Source → Any, Transform → Transform/Database  
**Prohibited:** Circular deps, self-loops, multiple sources  
**Validation:** On-drop with red dashed + error

### ELT Constraints
**Allowed:** Column filter, anonymization, row filter, coercion  
**Prohibited:** Joins, aggregations, pivot/unpivot, complex expressions, multiple inputs

### Canvas Features
Minimap (top-right), zoom/pan, fit view (double-click), snap-to-grid (20px), delete, duplicate (Ctrl+D), export via browser download or backend file APIs

### Pipeline Configuration
- **Schema:** `{version, nodes, edges, metadata}` required
- **Extension:** `.pipeline.json`
- **Validation:** Zod schema before save/load
- **Version:** Semver (`1.0.0`), auto-migrate old versions
- **Auto-Save:** Every 30s to localStorage or backend draft, limit 5MB

### Scalability
100+ nodes, <50ms pan/zoom, virtualize if needed

### Pre-Creation Search (MANDATORY)
Before creating or restyling any canvas node, SEARCH FIRST:
- `blueprints/canvas-node.svelte` (this skill) — structural scaffold to adapt from
- `app/frontend/src/lib/components/nodes/SourceNode.svelte` — canonical styles (planned location)
- `app/frontend/src/app.css` — `--node-*` and `--config-node-*` tokens
- `app/frontend/src/lib/components/Canvas.svelte` — interaction patterns (planned location)

### Prohibited
- Copying CSS from `app.css` into each node component
- Introducing new theme variables when existing tokens cover the need
- Hardcoding shadow/gradient values that diverge from the pipeline palette
- Silent overwrites, auto-save with no confirmation

## Cross-References
- [svelte-ui](../svelte-ui/SKILL.md): token system, component patterns, node configuration forms, validation
- [ui-security](../ui-security/SKILL.md): credential handling in node configs
- [data-contracts](../data-contracts/SKILL.md): Zod schema validation patterns

</ANCHORSKILL-UI-CANVAS>
