# Cross-References: Accessibility

## Adjacent Skills

| Skill | Relationship |
|-------|-------------|
| [svelte-ui](../../svelte-ui/SKILL.md) | SvelteKit component and form patterns — use alongside accessibility mandates when building UI components |
| [angular-forms-material](../../angular-forms-material/SKILL.md) | Angular form and Material component patterns — accessibility labels, ARIA on form controls |
| [angular-forms-material](../../angular-forms-material/SKILL.md) | Design tokens and color palettes — color contrast ratios trace here |
| [testing-debugging](../../testing-debugging/SKILL.md) | Governs when to write accessibility tests vs. debug keyboard nav failures |
| [ui-canvas](../../ui-canvas/SKILL.md) | Canvas/pipeline nodes are interactive — apply focus management and ARIA mandates |

## Source Utilities (SvelteKit / Framework-Agnostic)

These files in `app/frontend/src/lib/ui/utils/` implement the patterns described in this skill.
Blueprints mirror them; the source files are the authoritative implementation.

| File | Pattern |
|------|---------|
| `app/frontend/src/lib/ui/utils/focus-trap.ts` | Tab focus containment for modals/overlays |
| `app/frontend/src/lib/ui/utils/keyboard-nav.ts` | Arrow-key row navigation for lists and data tables |
| `app/frontend/src/lib/ui/utils/page-lock.ts` | Reference-counted scroll lock with `inert` attribute |
