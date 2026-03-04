# Checklist: RBAC Implementation

RBAC implementation checklist.

---

## Role System

- [ ] Roles: Viewer, Executor, Editor, Admin (exact names)
- [ ] Actions: view, audit, execute, edit, share, delete, manage_team
- [ ] Role matrix implemented correctly
- [ ] No custom roles or permissions

## Team Hierarchy

- [ ] Teams have parent_team_id for hierarchy
- [ ] Inheritance A algorithm implemented
- [ ] Direct membership overrides inheritance
- [ ] Nearest ancestor used if no direct membership
- [ ] Cycle detection in team hierarchy

## Resource Ownership

- [ ] Resources have owned_by_team_id column
- [ ] Authorization checks effective_role(user, owned_by_team_id)
- [ ] Client-sent team IDs never trusted
- [ ] Server sets owned_by_team_id on create

## Authorization Enforcement

- [ ] Centralized in src/backend/rbac/
- [ ] FastAPI dependencies used for auth
- [ ] No ad-hoc SQL permission checks in handlers
- [ ] List endpoints filter results by permission
- [ ] Object endpoints return 403 or 404 appropriately

## HTTP Responses

- [ ] 401 Unauthorized for not authenticated
- [ ] 403 Forbidden for authenticated but no permission
- [ ] 404 Not Found for resources user can't see
- [ ] Never leak existence of resources user can't access

## Frontend Integration

- [ ] Frontend consumes backend-provided roles
- [ ] No client-side permission logic
- [ ] UI elements hidden/disabled based on permissions
- [ ] Backend always re-checks permissions

## Audit Logging

- [ ] RBAC mutations logged
- [ ] Team changes logged
- [ ] Pipeline CRUD logged
- [ ] Log includes actor, target, changes, metadata
- [ ] Audit log immutable (insert-only)
