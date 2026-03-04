---
name: accessibility
description: "Governs Section 508 and WCAG 2.2 AA accessibility requirements: ARIA patterns, keyboard navigation, color contrast, focus management, and screen reader compatibility. Use when building any user-facing feature, auditing for accessibility compliance, or implementing interactive elements. DO NOT use for general Angular component patterns or Material token governance (see angular-forms-material)."
---

<ANCHORSKILL-ACCESSIBILITY>

# Accessibility (Section 508 / WCAG AA)

## Table of Contents & Resources

- [Core Concepts](#core-concepts)
- [SvelteKit Utilities](#sveltekit-utilities)
- [Angular CDK Accessibility](#angular-cdk-accessibility)
- [Blueprints](blueprints/) — `focus-trap.ts`, `keyboard-nav.ts`, `page-lock.ts`
- [Checklist: 508 Compliance](resources/checklist-508-compliance.md)
- [Reference: ARIA Patterns](resources/reference-aria-patterns.md)
- [Examples: Keyboard Navigation](resources/examples-keyboard-navigation.md)
- [Cross-References](resources/cross-references.md)

## Core Concepts

### Legal Requirement
All components and features MUST meet Section 508 and WCAG 2.2 Level AA standards. This is a legal requirement for State Government applications.

### Keyboard Navigation (MANDATED)

- All interactive elements must be keyboard accessible (Tab, Enter, Space, Arrow keys)
- Implement logical tab order using `tabindex` when necessary
- Ensure focus is visible with clear focus indicators
- Trap focus within modal dialogs

### Color and Contrast (MANDATED)

- Text contrast ratio: 4.5:1 minimum for normal text
- Large text (18pt+ or 14pt+ bold): 3:1 minimum
- UI components and graphics: 3:1 against adjacent colors
- NEVER use color alone to convey information

### Semantic HTML (MANDATED)

- Use semantic elements: `<button>`, `<nav>`, `<main>`, `<header>`, `<footer>`
- Use headings in logical order (h1 → h2 → h3, no skipping)
- Use lists for list content
- Use tables only for tabular data

### ARIA Usage

- Add ARIA labels when semantic HTML is insufficient
- Use `aria-label`, `aria-labelledby`, `aria-describedby`
- Use ARIA live regions for dynamic content: `aria-live="polite"` or `aria-live="assertive"`
- Set `aria-hidden="true"` for decorative elements
- Use `[attr.aria-disabled]="isReadOnly()"` when controlling disabled state programmatically via effects to maintain screen reader accessibility

### Target Size (WCAG 2.5.8, MANDATED)

- All interactive targets must be at least 24x24 CSS pixels (WCAG 2.2 Level AA)
- Primary touch targets (buttons, links, form controls) should be at least 44x44 CSS pixels
- Inline text links within paragraphs are exempt from the 24x24 minimum
- Ensure adequate spacing between adjacent interactive elements to prevent accidental activation

### Forms (MANDATED)

- Associate all inputs with visible `<label>` elements
- Use `<fieldset>` and `<legend>` for grouping related inputs
- Provide clear error messages with `aria-describedby`
- Mark required fields with `aria-required="true"` or `required`

### Images

- Provide `alt` text for all meaningful images
- Use empty `alt=""` for decorative images
- Complex images need `aria-describedby` with detailed descriptions

### SvelteKit Utilities

Framework-agnostic TypeScript utilities live in `app/frontend/src/lib/ui/utils/`.
Blueprints mirror the authoritative source files.

| Utility | Blueprint | Pattern |
|---------|-----------|---------|
| `focus-trap.ts` | [blueprints/focus-trap.ts](blueprints/focus-trap.ts) | Tab containment for modals/overlays |
| `keyboard-nav.ts` | [blueprints/keyboard-nav.ts](blueprints/keyboard-nav.ts) | Arrow-key row navigation for lists/tables |
| `page-lock.ts` | [blueprints/page-lock.ts](blueprints/page-lock.ts) | Reference-counted scroll lock with `inert` |

### Angular CDK Accessibility

- Use `A11yModule` for focus management
- Use `LiveAnnouncer` for dynamic announcements
- Use `FocusTrap` directive for modal dialogs

### Layout Overflow Prevention (MANDATED)

Horizontal scrollbars are a usability and accessibility failure:
- Keyboard users must navigate in two dimensions
- Screen readers may miss horizontally-scrolled content
- Mobile users face touch navigation difficulties

**Requirements**:
- Global `box-sizing: border-box` reset required in `src/style.scss`
- Elements using `width: 100%` must account for padding/borders
- Never rely on `overflow-x: hidden` to mask layout bugs
- Test all pages at minimum supported viewport width (320px mobile)

## Script Reference

### a11y-smoke.py
Run axe-core accessibility audit against web application routes.

`uv run a11y-smoke.py [--base-url <url>] [--routes <list>] [--output <path>] [--format markdown|json] [--level A|AA|AAA]`

| Arg | Purpose |
|-----|---------|
| `--base-url` | Base URL to test (default: http://localhost:4200) |
| `--routes` | Comma-separated routes to test (default: /,/login,/dashboard) |
| `--output` | Output file for report (default: stdout) |
| `--format` | Output format (default: markdown) |
| `--level` | WCAG conformance level (default: AA) |

</ANCHORSKILL-ACCESSIBILITY>
