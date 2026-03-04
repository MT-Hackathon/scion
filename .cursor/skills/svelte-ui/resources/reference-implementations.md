# Reference: Canonical Implementations

Source pointers to complete, production-grade implementations in the codebase. Read these when
the blueprint skeleton or examples don't cover edge cases — they show the full integration picture.

---

## FormPage Framework

**File:** `app/frontend/src/lib/ui/frameworks/FormPage.svelte`

The canonical form page component used throughout this app. Use this as the outer wrapper for any
full-page or drawer form. Key integration points:

- Accepts `onsubmit` as an async function — the component owns the `submitting` guard so callers
  never need to manage double-submit prevention themselves.
- `loading` prop (external) and internal `submitting` state are kept separate: `loading` reflects
  parent-driven async state (e.g., initial data fetch); `submitting` reflects the form's own
  in-flight submit. Both disable the submit button.
- The `actions` snippet overrides the default cancel/submit pair entirely — use when the form
  needs non-standard action arrangements (e.g., a multi-step footer with back/next).
- Error banner is rendered between header and content; pass an error string to surface backend
  failures without cluttering field-level validation.

See the blueprint skeleton at `../blueprints/form-page.svelte` for an adaptation-ready version
with structural vs. illustrative annotations.

---

## ListPage Framework Usage

**File:** `app/frontend/src/routes/dashboard/+page.svelte`

Complete example of `ListPage` in use: filter snippet, actions snippet, empty-state snippet,
drawer snippet, and row snippet all composed together. Demonstrates:

- `$derived` for filtered data reacting to filter state without explicit subscription wiring.
- Snippets (`{#snippet name(item)}`) as the composition pattern for per-row and drawer content.
- `loading` and `error` props threaded from page state into the framework component for uniform
  empty/error/loading states.
- `onretry` callback wired to reset error state for one-button recovery.

Use this as the reference when building any new list-style page. The dashboard page is intentionally
simple (mock data) to keep the pattern readable without domain noise.
