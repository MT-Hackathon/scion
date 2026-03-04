# Examples: FastAPI Authorization

See the structural scaffold in [`../blueprints/fastapi-authz-dependency.py`](../blueprints/fastapi-authz-dependency.py).

---

## Why FastAPI Dependencies, Not Handler Logic

The dependency injection approach enforces a hard architectural invariant: permission checks can never be accidentally skipped. When the check lives inside the handler, it can be omitted under deadline pressure or forgotten during refactors. When it is a `Depends(...)` argument, FastAPI makes it structurally impossible to call the route without the check running.

A secondary benefit: the `require_permission(action)` factory is composable. A route requiring both `"view"` and `"audit"` access declares both dependencies; FastAPI resolves them independently. No boolean logic in handlers.

---

## HTTP Response Semantics

| Scenario | Code | Reasoning |
|----------|------|-----------|
| Not authenticated | 401 | Identity not established |
| Authenticated, no permission | 403 | Identity known, access denied |
| Resource exists but user cannot see it | 404 | Never reveal existence via 403 |

The 404-for-invisible-resource rule is intentional information hiding. Returning 403 leaks that the resource exists, which is itself an authorization boundary violation in multi-tenant systems.

---

## Prohibited Pattern

Never perform ad-hoc permission checks inside route handlers:

```python
# BAD: permission logic leaks into the handler, easy to omit on new routes
@router.get("/pipelines/{id}")
async def get_pipeline(id: str):
    pipeline = db.get_pipeline(id)
    if not user_can_view(current_user, pipeline):  # ad-hoc check — prohibited
        raise HTTPException(403)
```

Authorization must flow through `authorize_action(user_id, resource_team_id, action)` in `src/backend/rbac/`. No SQL permission filters in handlers.
