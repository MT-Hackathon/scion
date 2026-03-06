---
name: ui-architecture
description: "Governs framework-agnostic UI architecture: layout ownership model (sandwich anti-pattern, one-owner-per-axis), overlay and portal patterns, z-index layering, scroll containment, theme system structure, responsive strategy (container queries over media queries), transition constraints, and design token hierarchy. Use when deciding layout approach, designing overlay/drawer/modal behavior, structuring a theme system, debugging layout failures, or reasoning about page-level composition. DO NOT use for Svelte-specific implementation (see svelte-ui), Angular Material tokens (see angular-forms-material), or accessibility compliance (see accessibility)."
---

<ANCHORSKILL-UI-ARCHITECTURE>

# UI Architecture

Framework-agnostic decisions about how the page is structured, how layers interact, and which component owns what.

## Table of Contents
- [Layout Ownership Model](#layout-ownership-model-mandated)
- [Push vs Overlay](#push-vs-overlay)
- [Portal and Overlay Architecture](#portal-and-overlay-architecture)
- [Z-Index Layering System](#z-index-layering-system)
- [Scroll Containment](#scroll-containment-mandated)
- [Theme System Architecture](#theme-system-architecture)
- [Token Mandates](#token-mandates)
- [Transition Constraints](#transition-constraints)
- [Dead Chrome](#dead-chrome)
- [Layout Debugging Order](#layout-debugging-order)
- [Epoch and Timestamp Safety](#epoch-and-timestamp-safety)
- [Prohibited Patterns](#prohibited-patterns)
- [Cross-References](#cross-references)

## Layout Ownership Model (MANDATED)

**Invariant**: Semantic components render content. Layout components own geometry. A component cannot be both. Violating this produces the sandwich anti-pattern.

**The Sandwich Anti-Pattern**: When a semantic component (list page, form page) owns both content and viewport geometry, any sibling detail panel gets trapped between its header/footer chrome. This recurs across frameworks because it feels natural — until the detail panel needs full height.

**One layout owner per axis**: Horizontal split = one component. Vertical scroll = one container. Nesting layout owners creates competing height contracts.

**One scroll owner per pane**: Each scrollable region has exactly one element with `overflow: auto/scroll`. Double-scroll (page AND inner container both scrolling) is always a bug.

**Master-detail composition**: The detail panel is a sibling of the entire master column, not a child of the list component. The layout component (e.g., `MasterDetailLayout`) owns the split; the list and detail are pure content.

## Push vs Overlay

- **Default to push** when the container can fit `minMasterWidth + drawerWidth + gutter` (~1160px typically).
- **Fallback to overlay** when the container is too narrow for side-by-side.
- **Use container queries, not viewport breakpoints.** Layout decisions come from the component's available space, not the window width. Viewport breakpoints break when the layout is embedded in a narrower host (iframe, split view, widget mode).
- **Push-mode panels are in-flow content** — they do NOT apply page lock, inert, or overlay backdrop.
- **Overlay-mode panels are modal** — they DO apply page lock, inert on `<main>`, and need a portal to escape the inert subtree.

## Portal and Overlay Architecture

**When portalling is required**: (1) escaping an `inert` subtree, (2) escaping a scroll container (`overflow: hidden` clips fixed-position children in some contexts), (3) escaping a stacking context that would clip or z-index-trap the overlay.

**Portal rule**: Move the overlay element to `document.body` via a portal action/directive. Svelte: `use:portal`. Angular: CDK Portal. React: `createPortal`.

**Theme inheritance problem**: Teleported overlays escape the theme context (e.g., `[data-theme='dark']` on `<html>`). Most portals land on `<body>` which inherits from `<html>`, so this works. But if the theme scope is narrower (e.g., on a container element), the overlay loses the theme. Fix: explicitly apply the theme attribute to the portal container.

**Focus trap scope**: Focus trapping applies to the portal'd content, not the original mount point. Keyboard events (Tab, Escape) must be handled inside the portal'd element.

## Z-Index Layering System

Canonical layers — use CSS custom properties, not raw integers:

```css
--z-content:    0     /* Default content */
--z-sticky:     10    /* Sticky headers, toolbars */
--z-dropdown:   20    /* Select menus, popovers */
--z-drawer:     30    /* Side panels (push mode — rarely needs z-index) */
--z-sidebar:    40    /* App navigation sidebar */
--z-modal:      50    /* Modals, overlay drawers, dialogs */
--z-toast:      60    /* Toast notifications */
--z-critical:   9999  /* Error overlays, crash screens */
```

**Anti-pattern**: z-index arms race — incrementing z-index to "fix" stacking. If two elements compete for z-index, one of them is in the wrong stacking context.

**Stacking context creation**: `position: fixed/sticky`, `transform`, `opacity < 1`, `will-change`, `filter`, `isolation: isolate` all create new stacking contexts. Know which containers create them before adding any overlay.

## Scroll Containment (MANDATED)

- The scroll owner for each pane must have a bounded height (via flex, grid, or explicit height). Without a bounded ancestor, `overflow: auto` does nothing.
- `min-height: 0` is required on flex children that should shrink below their content height. Without it, flex children grow to fit content and prevent scrolling.
- `overflow: hidden` on a parent clips `position: absolute` children but NOT `position: fixed` children (fixed is relative to the viewport). Don't use `overflow: hidden` as a z-index or stacking fix.
- **Page lock pattern**: Reference-counted lock (`lockCount++` on open, `lockCount--` on close). Set `document.body.style.overflow = 'hidden'` and `main.inert = true` only when `lockCount > 0`. Ensures multiple overlays don't fight.

## Theme System Architecture

**Universal flow**: Config source → runtime store → CSS variable sync → component consumption.

**Attribute toggling**: Use `data-theme` (or `data-color-scheme`) on `<html>` or `<body>`. All theme-dependent styles reference CSS custom properties set under `[data-theme='light']` and `[data-theme='dark']` selectors.

**Three-tier token hierarchy**: Primitive (raw values, color scales) → Semantic (intent: `--bg-primary`, `--text-secondary`) → Component (scoped: `--button-primary-bg`, `--table-header-bg`).

**Overlay container problem**: Teleported overlays must inherit the active theme. If using `document.body` as portal target and `[data-theme]` is on `<html>`, inheritance works naturally. If the theme scope is narrower, explicitly sync the attribute to the portal container.

**OS preference**: Respect `prefers-color-scheme` as default, allow user override stored locally.

## Token Mandates

- No hardcoded color values or layout dimensions when tokens exist. All values from `var(--token)` or utility classes.
- Semantic state tokens required: success, warning, info, error — each with bg, text, and border variants.
- Use `light-dark()` CSS function for semantic tokens that need both schemes in one declaration (when browser support allows).

## Transition Constraints

- **GPU-composited properties only for layout transitions**: `transform`, `opacity`. These don't trigger layout recalculation.
- **Never transition structural properties**: `width`, `height`, `margin`, `padding`, `top`/`left`. These trigger layout reflow on every frame.
- **`transition-colors` restriction**: Only on interactive elements (buttons, links, nav items). NEVER on structural/container elements (divs, sections, aside, main, layout wrappers). Theme switching should be a hard cut, not an animation — mixed transition speeds create a visible cascade across the page.

## Dead Chrome

A fixed UI element that permanently consumes viewport space for controls that could live elsewhere (sidebar footer, inline, on-demand menu) is dead chrome. Modern apps maintain fixed headers/bars only when they carry global primitives — search, context switching, breadcrumbs, navigation.

**Rule**: Eliminate fixed bars that hold only one or two secondary controls. Move those controls to the sidebar footer or an inline position.

## Layout Debugging Order

When a layout looks wrong, diagnose in this order:

1. **Box model** — is the element the size you expect? Check padding, border, margin.
2. **Containing block** — which ancestor establishes the coordinate system? `position: relative/absolute/fixed` confusion is the #1 cause.
3. **Scroll container** — which element owns `overflow`? Is its height bounded? Is `min-height: 0` set on flex children?
4. **Stacking context** — is a `transform`, `opacity`, or `will-change` creating an unexpected stacking context?
5. **Z-index layer** — is the element in the correct canonical layer?

## Epoch and Timestamp Safety

When formatting timestamps for display, guard against stale or migrated data:

- Don't trust `epochMs > 0` — small positive values (like `1`) are technically positive but epoch-adjacent (render as "12/31/1969" in US timezones).
- Use a floor date: `if (epochMs < Date.UTC(2020, 0, 1)) return 'Never'` or equivalent.
- This applies to any system that migrates timestamp storage formats.

## Prohibited Patterns

- Semantic component owning viewport geometry for a sibling pane
- `transition-colors` on structural or layout elements
- Viewport media queries for interior layout dimensions (use container queries)
- Overlay rendered inside an `inert` subtree without a portal action
- Fixed header or bar holding only secondary controls
- Z-index arms race (incrementing z-index without understanding stacking contexts)
- Double-scroll (page AND inner container both scrolling)
- `overflow: hidden` used as a stacking or z-index fix

## Cross-References

- [svelte-ui](../svelte-ui/SKILL.md): Svelte/Tailwind token implementation, component catalog, portal action.
- [angular-forms-material](../angular-forms-material/SKILL.md): Angular Material token implementation, overlay container sync.
- [accessibility](../accessibility/SKILL.md): ARIA requirements for overlays, keyboard navigation, scroll impact.
- [visual-qa](../visual-qa/SKILL.md): Layout regression detection methodology.
- [tauri-development](../tauri-development/SKILL.md): Tauri window constraints, WebView viewport behavior.

</ANCHORSKILL-UI-ARCHITECTURE>
