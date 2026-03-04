# Reference: Component Catalog

Source pointers to canonical in-repo implementations. Read these when blueprints are insufficient or when adapting a complex pattern that goes beyond the structural skeleton.

---

## Accelerator Components (primary use — prefer over native elements)

| Component | Path | What it demonstrates |
| :--- | :--- | :--- |
| `Button` | `app/frontend/src/lib/ui/Button.svelte` | Variant system, loading state with branded GraftMark, shimmer animation, bits-ui Root |
| `Input` | `app/frontend/src/lib/ui/Input.svelte` | Form field pattern with ARIA wiring, label/description/error snippets, `$bindable` |
| `Select` | `app/frontend/src/lib/ui/Select.svelte` | Controlled select with bits-ui, option rendering, ARIA |
| `DataTable` | `app/frontend/src/lib/ui/DataTable.svelte` | Complex table with keyboard navigation, responsive layout, column slot API |
| `Pagination` | `app/frontend/src/lib/ui/Pagination.svelte` | Page control integration pattern |
| `FilterBar` | `app/frontend/src/lib/ui/FilterBar.svelte` | Filter input composition |
| `Badge` | `app/frontend/src/lib/ui/Badge.svelte` | Status badge with semantic color tokens |

## Overlay and Focus-Trap Patterns

| Component | Path | What it demonstrates |
| :--- | :--- | :--- |
| `Dialog` | `app/frontend/src/lib/ui/Dialog.svelte` | Modal dialog with portal rendering, focus trap, entry/exit animation, backdrop |
| `DrawerPeek` | `app/frontend/src/lib/ui/DrawerPeek.svelte` | Slide-in drawer with focus trap, page scroll lock, overlay dismiss |
| `Tooltip` | `app/frontend/src/lib/ui/Tooltip.svelte` | Floating tooltip with bits-ui positioning |

## Page Framework Components

For complete page-level patterns (sorting, pagination, drawer integration) see the frameworks directory:

| Component | Path | What it demonstrates |
| :--- | :--- | :--- |
| `ListPage` | `app/frontend/src/lib/ui/frameworks/ListPage.svelte` | Full list view with sort headers, pagination, loading/empty/populated states, drawer peek integration |
| `FormPage` | `app/frontend/src/lib/ui/frameworks/FormPage.svelte` | Form layout framework with section structure and action bar |

## Blueprints (adaptation-ready skeletons)

These distill the structural patterns above into minimal, annotated skeletons:

- [`blueprints/variant-component.svelte`](../blueprints/variant-component.svelte) — variant union + Record lookup + `$derived` class composition
- [`blueprints/form-field.svelte`](../blueprints/form-field.svelte) — `$bindable` field with ARIA wiring and error state
