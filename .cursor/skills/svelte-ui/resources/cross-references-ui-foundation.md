# Cross-References: Svelte UI Foundation Segment

Adjacent skills and their scope boundaries.

---

## Adjacent Skills

| Skill | What it governs | When to use it instead |
| :--- | :--- | :--- |
| [ui-canvas](../../ui-canvas/SKILL.md) | SvelteFlow canvas, node types, pipeline configuration, edge validation | Any work on the pipeline canvas or node rendering |
| [svelte-ui](../../svelte-ui/SKILL.md) | Forms, validation logic, HTTP communication, reactive state management | User input handling, API calls from the frontend, form validation |
| [ui-security](../../ui-security/SKILL.md) | Auth token storage, API key handling, XSS prevention, HTTP security headers | Frontend authentication flows, credential management |
| [fullstack-workflow](../../fullstack-workflow/SKILL.md) | Cross-stack type synchronization, backend-UI integration debugging | Work spanning both FastAPI backend and SvelteKit frontend |
| [accessibility](../../accessibility/SKILL.md) | Section 508 / WCAG 2.2 AA, ARIA patterns, focus management, screen readers | Auditing for accessibility compliance or implementing interactive ARIA patterns |

## Defined Anchors

- `ANCHORSKILL-SVELTE-UI`: top of `SKILL.md` — frontend foundation + data flow patterns

## Key Principles

- **Tech Stack:** SvelteKit 5, Vite, Tailwind v4, TypeScript strict, bits-ui for accessibility primitives
- **Tokens:** CSS variables via `$lib/tokens/tokens.css` — three tiers: primitive -> semantic -> component
- **Components:** Svelte 5 syntax mandatory (`$props()`, `$derived`, `$state`, `$effect`)
- **State:** Form values bind to shared stores or parent-owned state, never local component variables
- **Debugging:** Browser tools for verification; never declare success without screenshot
