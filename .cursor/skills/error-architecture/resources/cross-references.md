# Cross-References: Error Architecture

Related skills/rules and anchors.

---

## Related Skills/Rules
- [012-constitution-universal](../../../rules/012-constitution-universal/RULE.mdc): Guard clauses and universal coding invariants
- [svelte-ui](../../svelte-ui/SKILL.md): HTTP error handling in the frontend form/data layer
- [fullstack-workflow](../../fullstack-workflow/SKILL.md): Cross-stack error debugging
- [testing-debugging](../../testing-debugging/SKILL.md): Systematic diagnosis and two-attempt rule

## Defined Anchors
- `ANCHORSKILL-ERROR-ARCHITECTURE`: Error handling mandate (SKILL.md)

## Source Pointers
- `app/backend/src/graft/errors.py`: Domain error hierarchy (base class + typed subclasses)
- `app/backend/src/routers/graft_router.py` · `_problem()`: RFC 7807 HTTP envelope + typed catch pattern
- `app/backend/src/graft/constants.py` · `ErrorTitle`: Mandated HTTP error title strings
