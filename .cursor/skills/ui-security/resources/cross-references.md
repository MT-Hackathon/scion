# Cross-References: UI Security

Related skills and anchors.

---

## Related Skills

- [security](../../security/SKILL.md): Backend security mandates (credential vaults, auth flows, secrets management)
- [svelte-ui](../../svelte-ui/SKILL.md): UI tech stack constraints, forms, validation, and HTTP communication patterns

## Defined Anchors

- `ANCHORSKILL-UI-SECURITY`: UI security mandate

## Key Principles

- **Credentials:** Backend vaults only, never client persistence
- **Exposure:** Mask logs, no credentials in errors/console/URLs
- **APIs:** Standard browser APIs only, no native/desktop access
- **Payloads:** Zod validation, size limits, input sanitization
