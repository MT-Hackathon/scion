# Checklist: Node Creation

Pre-flight checklist for creating or restyling canvas nodes.

---

## Mandatory Search Locations

Before creating or restyling any canvas node, check these locations first:

- [ ] `blueprints/canvas-node.svelte` (this skill) for the structural node scaffold
- [ ] `app/frontend/src/lib/components/nodes/SourceNode.svelte` (planned canonical) for gradients, borders, shadows, pseudo-elements, and handle states
- [ ] `app/frontend/src/app.css` for shared `--node-*` and `--config-node-*` tokens
- [ ] `app/frontend/src/lib/components/Canvas.svelte` (planned) for edge deletion, handle glow, selection feedback, and interaction wiring

## Validation Steps

1. [ ] Confirm styling gradients and shadows match `SourceNode` reference (140° light, 150° dark, same `color-mix` percentages, `::after` highlight) — adapt from `blueprints/canvas-node.svelte` when canonical doesn't exist yet
2. [ ] Use shared tokens (`--node-color-*`, `--node-gradient-*`, `--node-border-*`, `--node-shadow-*`, `--node-handle-*`, `--config-node-*`) instead of hardcoded values
3. [ ] Verify handle classes (`.config-node-handle`, `.source-handle`) reuse glow/connected patterns from `app.css` and `Canvas.svelte`
4. [ ] If node can be selected/connected, ensure edge deletion/selection UI copies from `Canvas.svelte`
5. [ ] Confirm drag-over/drop handling, palette MIME types (`CONFIG_NODE_MIME`), and config canvas store usage exist before re-implementing

## Node Structure

- [ ] Use `<script lang="ts">`
- [ ] Define props with `NodeProps` type from `@xyflow/svelte`
- [ ] Implement `selected` state styling
- [ ] Use design tokens from `cssVariableSync.ts`
- [ ] Follow gradient, shadow, overlay sequence
- [ ] Test with both light and dark themes

## Handle Implementation

- [ ] Handles use `--node-handle-size` for dimensions
- [ ] Handles use `--node-handle-border-width` for border
- [ ] Handles show glow on hover/connected via `--node-handle-shadow-width`
- [ ] Handle position matches node type (out-only for source, in-only for target)

## Anti-patterns (Code Review Reject)

- [ ] NOT copying CSS from `app.css` into each node component
- [ ] NOT introducing new theme variables when existing tokens cover the need
- [ ] NOT hardcoding shadow/gradient values that diverge from the pipeline palette
- [ ] NOT skipping `Canvas.svelte` when adding features like edge deletion or handle glow
