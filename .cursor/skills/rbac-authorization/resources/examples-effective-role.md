# Examples: Effective Role Calculation

See the canonical implementation in [`../blueprints/effective-role.py`](../blueprints/effective-role.py).

---

## Why This Resolution Order

Inheritance A is designed so that explicit grants always beat inherited ones. The override/baseline split on a direct membership record lets admins say "this user gets Editor here specifically, regardless of what role they'd inherit from a parent team." Without the override field, you cannot grant an escalated role on a sub-team without changing the parent — which breaks the principle of least surprise for the rest of the organization.

Ancestor traversal stops at the nearest match (closest to `team_id` in the hierarchy). This means a role granted at an intermediate team does not get silently overridden by a more-permissive grant higher up the tree. Access tightens as you descend; it never secretly relaxes.

Returning `None` (not a string like `"None"` or an empty role) is the signal that the user has no access path. `authorize_action` treats `None` as unconditional deny.

---

## Inheritance Resolution Table

| Scenario | Effective Role |
|----------|---------------|
| Direct membership, `role_override` set | `role_override` |
| Direct membership, no override | `role_baseline` |
| No direct membership, nearest ancestor has membership | Ancestor's `role_override or role_baseline` |
| No membership anywhere in hierarchy | `None` (deny) |

---

## Cycle Detection

`get_ancestor_teams` must be cycle-safe. A naive recursive walk on a malformed `parent_team_id` graph will infinite-loop. Use a visited set and stop when a team_id is seen twice. Surface cycle detection as a data integrity violation, not a silent truncation.

---

## List Endpoints vs Object Endpoints

For list endpoints: filter — do not return resources the user cannot see, do not error.  
For object endpoints: if the user cannot `"view"` the resource, return `404` (not `403`) to avoid leaking existence. See `examples-fastapi-authz.md` for the HTTP semantics rationale.
