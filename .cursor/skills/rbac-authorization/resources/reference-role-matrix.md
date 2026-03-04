# Reference: Role Matrix

Role to actions mapping table.

---

## Role Matrix

| Role | Actions |
|------|---------|
| Viewer | view, audit |
| Executor | view, audit, execute |
| Editor | view, audit, execute, edit, share |
| Admin | view, audit, execute, edit, share, delete, manage_team |

---

## Actions Reference

| Action | Description |
|--------|-------------|
| `view` | Read resource data |
| `audit` | View audit logs for resource |
| `execute` | Execute pipelines |
| `edit` | Modify resource configuration |
| `share` | Grant access to other users/teams |
| `delete` | Remove resource permanently |
| `manage_team` | Add/remove team members, change roles |

---

## Role Inheritance

Roles are cumulative. Each role includes all permissions of roles below it:

```
Admin    → [all actions]
    ↑
Editor   → [view, audit, execute, edit, share]
    ↑
Executor → [view, audit, execute]
    ↑
Viewer   → [view, audit]
```

---

## Authorization Check

```python
def authorize_action(user_id: str, resource_team_id: str, action: str) -> bool:
    """Check if user can perform action on resource."""
    role = effective_role(user_id, resource_team_id)
    if not role:
        return False
    
    allowed_actions = {
        "Viewer": ["view", "audit"],
        "Executor": ["view", "audit", "execute"],
        "Editor": ["view", "audit", "execute", "edit", "share"],
        "Admin": ["view", "audit", "execute", "edit", "share", "delete", "manage_team"]
    }
    
    return action in allowed_actions.get(role, [])
```
