# Examples: Audit Logging

Audit log write pattern for RBAC mutations.

---

## Pattern

Log all RBAC/team/share mutations and pipeline CRUD with actor, target, changes, and request metadata.

---

## Project Implementation

```python
def write_audit_log(
    actor_id: str,
    action: str,
    target_type: str,
    target_id: str,
    changes: dict,
    request_metadata: dict
):
    """Write audit log entry."""
    db.insert("audit_log", {
        "timestamp": datetime.utcnow(),
        "actor_id": actor_id,
        "action": action,
        "target_type": target_type,
        "target_id": target_id,
        "changes": json.dumps(changes),
        "ip_address": request_metadata.get("ip"),
        "user_agent": request_metadata.get("user_agent")
    })
```

---

## Usage Example

```python
write_audit_log(
    actor_id=current_user.id,
    action="pipeline.create",
    target_type="pipeline",
    target_id=new_pipeline.id,
    changes={"name": "My Pipeline", "owned_by_team_id": team.id},
    request_metadata={
        "ip": request.client.host,
        "user_agent": request.headers.get("user-agent")
    }
)
```

---

## Actions to Log

| Action | When |
|--------|------|
| `pipeline.create` | New pipeline created |
| `pipeline.update` | Pipeline config changed |
| `pipeline.delete` | Pipeline removed |
| `team.member_add` | User added to team |
| `team.member_remove` | User removed from team |
| `team.role_change` | User role changed |
| `share.grant` | Access granted to user/team |
| `share.revoke` | Access revoked |

---

## Audit Log Schema

| Column | Type | Description |
|--------|------|-------------|
| timestamp | datetime | When action occurred |
| actor_id | string | User who performed action |
| action | string | Action type (e.g., `pipeline.create`) |
| target_type | string | Resource type (e.g., `pipeline`) |
| target_id | string | Resource ID |
| changes | json | Before/after values |
| ip_address | string | Client IP |
| user_agent | string | Client user agent |
