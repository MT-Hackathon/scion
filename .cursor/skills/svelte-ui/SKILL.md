---
name: svelte-ui
description: "Governs SvelteKit/Svelte 5 component patterns, Zod validation, HTTP communication, reactive state management, design token CSS variable system (primitive/semantic/component tiers), page framework components (ListPage/FormPage), drawer and overlay implementations (DrawerPeek/Dialog), and template rendering performance. Use when building Svelte components, implementing forms, working with the Svelte/Tailwind design token system, debugging Svelte-specific layout or drawer implementations, handling user input, or calling APIs. For framework-agnostic layout architecture, see ui-architecture. DO NOT use for canvas/pipeline patterns (see ui-canvas), security requirements (see ui-security), or accessibility compliance (see accessibility)."
---

<ANCHORSKILL-SVELTE-UI>

# Svelte UI

## Table of Contents
- [Core Concepts](#core-concepts)
- [Svelte 5 Syntax (MANDATORY)](#svelte-5-syntax-mandatory)
- [Token System and Styling (MANDATED)](#token-system-and-styling-mandated)
- [Layout Architecture](#layout-architecture)
- [Form and Validation Model (MANDATED)](#form-and-validation-model-mandated)
- [HTTP Communication Model (MANDATED)](#http-communication-model-mandated)
- [Loading and Display States (MANDATED)](#loading-and-display-states-mandated)
- [Template Rendering Performance (MANDATED)](#template-rendering-performance-mandated)
- [Pre-Creation Search (MANDATORY)](#pre-creation-search-mandatory)
- [Prohibited Patterns](#prohibited-patterns)
- [Resources](#resources)
- [Blueprints](#blueprints)
- [Cross-References](#cross-references)

## Core Concepts

### Stack and Runtime
- **Frontend:** SvelteKit 5, Vite, Tailwind v4, TypeScript strict mode, Node 20 LTS.
- **Deployment:** SPA mode via `@sveltejs/adapter-static`; backend communication via Tauri IPC (`invoke()`), not HTTP. For web-only deployments (e.g., Universal-API), `@sveltejs/adapter-node` with HTTP to FastAPI applies.
- **UI Library:** Prefer accelerator components in `$lib/ui/` for consistency, accessibility wiring, and token compliance.

### Brand and Design System
- Design tokens are authoritative and flow through CSS variables (primitive -> semantic -> component).
- Theme modes are light and dark via `data-theme`; components consume tokens through Tailwind utilities or `var(--token)`.
- `GraftMark` in `$lib/ui/` is the branded mark and loading indicator for async button operations.

## Svelte 5 Syntax (MANDATORY)

| Svelte 4 (NEVER) | Svelte 5 (ALWAYS) |
| ---------------- | ----------------- |
| `export let prop` | `let { prop } = $props()` |
| `$: derived = value` | `let derived = $derived(value)` |
| `$: { sideEffect() }` | `$effect(() => { sideEffect() })` |
| `let count = 0` (reactive) | `let count = $state(0)` |
| `<slot />` | `{@render children?.()}` with `Snippet` |
| `on:click={handler}` | `onclick={handler}` |

## Token System and Styling (MANDATED)

- Components MUST consume styling via shared tokens; never hardcode per-component color values.
- Use Tailwind token-mapped classes for standard styling and `var(--token)` for complex cases.
- Theme switches update CSS variables through settings store + CSS sync; components should not implement theme logic directly.
- For forms and controls, prefer shared class families and accelerator components over ad hoc styling.

## Layout Architecture

See `ui-architecture` skill for the universal layout ownership model, push/overlay decision criteria, portal architecture, scroll containment, and z-index layering. This section covers Svelte-specific implementation.

### App-Shell Scroll Model (MANDATED)

This app uses a **fixed viewport app-shell**: `<main>` clips via `overflow-hidden` and does NOT scroll. Every route must provide its own scroll container.

Required scroll containment chain:
```
<div class="flex h-dvh">               ← root, deterministic height (NOT min-h-screen)
  <div class="flex flex-1 flex-col min-h-0">  ← content column, min-h-0 required
    <main class="flex-1 min-h-0 overflow-hidden">  ← clipping host, NOT scroll owner
      <!-- route content here — must own its own scroll -->
```

**Route mandate**: Every route component must wrap its content in a scroll container. Flat layouts use `<div class="h-full overflow-y-auto">`. Master-detail layouts use `MasterDetailLayout` (which provides pane-level scrolling internally). No route may rely on page-level scroll.

**`h-dvh` vs `min-h-screen`**: Use `h-dvh` (dynamic viewport height) for deterministic flex containment chains. `min-h-screen` creates a minimum bound but does not cap height, making scroll containment unreliable.

**Mode switching with ResizeObserver**: Layout components that switch between push and overlay modes based on container width use `ResizeObserver` (not CSS `@container`). CSS container queries cannot reach Svelte `$state`. Pattern:
```svelte
$effect(() => {
  if (!containerEl) return;
  const ro = new ResizeObserver(([entry]) => {
    if (!entry) return;
    mode = entry.contentRect.width >= threshold ? 'push' : 'overlay';
  });
  ro.observe(containerEl);
  return () => ro.disconnect();
});
```

### Svelte Portal Action
The `portal` action at `$lib/ui/utils/portal.ts` moves a DOM node to `document.body` on mount and removes it on destroy. Use in overlay mode to escape `inert` subtrees:

```svelte
{#if open}
  <div use:portal>
    <!-- overlay content -->
  </div>
{/if}
```

Push-mode panels do NOT use portal — they are in-flow flex siblings.

### Page Lock Implementation
`$lib/ui/utils/page-lock.ts` implements reference-counted scroll locking. Only overlay-mode drawers call `setPageLock(true)`. Push-mode drawers call focus management only.

## Form and Validation Model (MANDATED)

### Input and Store Ownership
- Use accelerator `Input` for text inputs unless it is functionally unsuitable.
- Form values bind to central store/resource or parent-owned state; never isolated per-component form state.
- For configurable forms, use store factory patterns (`state`, `errors`, `updateField`, `validate`, `reset`) and pass values/errors/change handlers to nested components.

### Zod Validation (MANDATED)
- Zod schemas are required for type-safe validation and boundary checks.
- Use `.safeParse()` for user input and map issues into field-level error state.

### Validation Timing (REQUIRED)
- **Blur:** immediate field validation.
- **Change:** debounced validation (300ms).
- **Submit:** full schema validation before submit side effects.
- **Display:** inline field errors and top-level summary for form-wide failures.

### Error Messaging (REQUIRED)
- Error messages must be actionable, concise, and specific.
- When possible, include auto-fix guidance (for example expected URL scheme).

### Responsive Form Layouts (MANDATED)
- Prefer flex layouts for variable-height form fields.
- Use grid only when strict row/column alignment is required.

## HTTP Communication Model (MANDATED)

- UI communicates with backend exclusively through HTTP fetch to `/api/*`; no custom bridges.
- Base URL must come from `VITE_API_URL`; request headers include content-type and required session headers.
- Backend envelope contract:
  - `success: boolean`
  - `data` on success
  - `error: { code, message }` on failure
- Surface backend failures in UI; do not swallow or silently mask errors.
- Type-check backend responses with TypeScript unions and/or Zod parsing where risk is high.

### Timeouts and Polling
- Use `AbortController` for explicit request timeout control.
- Default timeout strategy: fast-start requests around 5s; increase up to 30s for long polling/backoff loops.
- Retry logic may exist in UI, but never suppress terminal backend errors.

## Loading and Display States (MANDATED)

- Use `Button` `loading` prop for async actions and branded in-button loading.
- Use `.skeleton` for page-level loading over 200ms.
- During loading, disable conflicting UI actions and expose `role="status"` with `aria-live="polite"` when applicable.
- Data-backed views render one primary state at a time:
  - Loading
  - Empty
  - Populated
- Never show stale populated content beneath loading or empty state views.

## Template Rendering Performance (MANDATED)

- Do not call compute functions directly in template expressions for derived display state.
- Precompute display state in `$derived(...)` / `$derived.by(...)` and bind the result.
- Every dynamic `{#each}` block must include a stable key (`item.id` or equivalent unique identity).
- Never use array index keys for reorderable, filterable, or mutable collections.

## Pre-Creation Search (MANDATORY)

Before adding or refactoring Svelte forms/components, search canonical implementations first:
- Framework components for list/form page structure patterns.
- Shared form utilities and validation helpers (`$lib/utils/validation.ts`, related form config modules).
- Shared token and class definitions in app-level CSS.
- Existing accelerator components in `$lib/ui/`.

## Prohibited Patterns

- No native/desktop wrappers, IPC bridges, window hacks, or non-HTTP transport from UI.
- No inline error swallowing or hidden backend failures.
- No hardcoded color values where shared tokens already cover the need.
- No inline hex/rgb color literals or per-component color variable systems.
- No unkeyed dynamic lists or index keys for mutable collections.
- No plain visible `<input>` where accelerator `Input` is appropriate.
- No creation of divergent select/input class systems outside shared token patterns.
- No bypassing settings/token synchronization flow.
- No `goto()` in `onMount` for route redirects; use SvelteKit server-side `redirect()`.
- For layout-related prohibited patterns (semantic components owning viewport geometry, transition-colors on structural elements, etc.), see `ui-architecture` Prohibited Patterns.

## Resources
- `resources/reference-tech-stack.md` — SvelteKit architecture and environment/deployment patterns
- `resources/reference-tokens.md` — token hierarchy and CSS variable usage patterns
- `resources/reference-svelte5-syntax.md` — Svelte 5 rune syntax migration and examples
- `resources/reference-component-catalog.md` — source pointers to canonical accelerator components
- `resources/examples-component-patterns.md` — component usage examples for accelerator library
- `resources/examples-css-patterns.md` — loading and styling state examples
- `resources/guide-debugging-workflow.md` — browser-first UI debugging and verification flow
- `resources/guide-settings-framework.md` — settings store and CSS sync architecture
- `resources/checklist-component-creation.md` — component and token pre-flight checklist
- `resources/reference-implementations.md` — canonical form/list integration pointers
- `resources/reference-validation-timing.md` — blur/change/submit validation timing details
- `resources/reference-http-envelope.md` — API envelope contract and type-safe handling
- `resources/examples-form-patterns.md` — form store composition and nested input patterns
- `resources/examples-http-patterns.md` — HTTP timeout, polling, and error surfacing patterns
- `resources/guide-test-endpoint.md` — test endpoint UX/state pattern
- `resources/checklist-form-creation.md` — form refactor/create audit checklist
- `resources/cross-references-ui-foundation.md` — preserved cross-reference snapshot from the legacy foundation split
- `resources/cross-references-ui-data-flow.md` — preserved cross-reference snapshot from the legacy data-flow split

## Blueprints
- `blueprints/variant-component.svelte` — variant union + record lookup + derived class composition
- `blueprints/form-field.svelte` — bindable field with ARIA/error wiring
- `blueprints/form-page.svelte` — form layout with guarded async submit and action bar

## Cross-References
- [ui-architecture](../ui-architecture/SKILL.md): framework-agnostic layout ownership model, push/overlay decisions, portal architecture, scroll containment, z-index layering, and three-tier token hierarchy.
- [ui-canvas](../ui-canvas/SKILL.md): canvas/pipeline rendering, node/edge rules, pipeline persistence.
- [ui-security](../ui-security/SKILL.md): credential handling, frontend security boundaries, payload constraints.
- [accessibility](../accessibility/SKILL.md): WCAG/Section 508 ARIA, keyboard, and assistive-tech requirements.
- [api-design](../api-design/SKILL.md): backend request/response contract design and API schema boundaries.
- [fullstack-workflow](../fullstack-workflow/SKILL.md): backend/frontend type synchronization and cross-boundary debugging.
- [data-contracts](../data-contracts/SKILL.md): API boundary validation and schema alignment policy.

</ANCHORSKILL-SVELTE-UI>
