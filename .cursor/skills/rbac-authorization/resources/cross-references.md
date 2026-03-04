# Cross-References: RBAC Authorization

Related skills and anchors.

---

## Related Skills

- [security](../security/SKILL.md): Authentication (who you are); JWT/OAuth patterns; credential management. RBAC governs what an authenticated identity may do.
- [error-architecture](../error-architecture/SKILL.md): HTTP error response contracts (401/403/404 semantics defined there).

## Blueprints

- [`blueprints/fastapi-authz-dependency.py`](../blueprints/fastapi-authz-dependency.py): `require_permission` factory — use as starting point for any protected route.
- [`blueprints/effective-role.py`](../blueprints/effective-role.py): Inheritance A algorithm — canonical `effective_role` and `authorize_action` implementations.

## Defined Anchors

- `ANCHORSKILL-RBAC-AUTHORIZATION`: RBAC authorization mandate (SKILL.md)

## Key Concepts

- **Authentication:** Who you are — see `security` skill.
- **Authorization:** What you can do — this skill.
- **Roles:** `Viewer < Executor < Editor < Admin` (cumulative, additive)
- **Inheritance A:** direct override → direct baseline → nearest ancestor → None
- **Ownership:** `owned_by_team_id` on resources; never trust client-sent values
