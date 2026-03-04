# Cross-References: Svelte UI Data Flow Segment

Related skills and anchors.

---

## Related Skills

- [svelte-ui](../../svelte-ui/SKILL.md): Unified Svelte component, form, and HTTP communication guidance
- [ui-canvas](../../ui-canvas/SKILL.md): Node configuration forms and SvelteFlow canvas patterns
- [ui-security](../../ui-security/SKILL.md): Credential handling, API key storage, payload validation
- [data-contracts](../../data-contracts/SKILL.md): Schema validation, type synchronization at API boundary
- [fullstack-workflow](../../fullstack-workflow/SKILL.md): Cross-stack debugging, type alignment across backend and frontend

## Defined Anchors

- `ANCHORSKILL-SVELTE-UI`: Form and HTTP communication patterns (merged skill anchor)

## Key Principles

- **Validation:** Zod schemas, blur/change/submit timing, inline errors
- **Forms:** FormPage framework for structure; Zod for validation; never local state
- **HTTP:** Envelope format `{ success, data, error }`, surface all errors, AbortController for timeouts
- **Test Endpoint:** 10s timeout, redact credentials, specific error messages
