---
name: rbac-authorization
description: "Governs Universal-API RBAC invariants: teams, role inheritance, ownership, sharing, and audit requirements. Use when adding/modifying endpoints or UI that are user/team scoped, or when implementing SCIM/team membership/sharing. DO NOT use for general authentication (see security) or session boundary cleanup."
---

<ANCHORSKILL-RBAC-AUTHORIZATION>

# RBAC Authorization Rule

## Table of Contents & Resources

**Blueprints** (copy-paste scaffolds)
- [FastAPI Auth Dependency](blueprints/fastapi-authz-dependency.py) — `require_permission` factory for protected routes
- [Effective Role Algorithm](blueprints/effective-role.py) — Inheritance A: `effective_role` + `authorize_action`

**Resources** (governance, narration, reference)
- [Core Concepts](#core-concepts)
- [Reference: Role Matrix](resources/reference-role-matrix.md)
- [Examples: Effective Role](resources/examples-effective-role.md)
- [Examples: FastAPI Authorization](resources/examples-fastapi-authz.md)
- [Examples: Audit Logging](resources/examples-audit-logging.md)
- [Checklist: RBAC Implementation](resources/checklist-rbac-impl.md)
- [Cross-References](resources/cross-references.md)

## Core Concepts

### Activation
User message contains: "rbac", "team", "teams", "role", "permission", "authz", "authorize", "sharing", "owned_by_team_id", "SCIM", "Okta", "audit log"

### Core Invariants (MANDATED)
- **Tenancy:** per-agency container; no runtime multi-tenancy; do not add org_id columns/filters.
- **Roles (exact):** Viewer|Executor|Editor|Admin
- **Actions:** view audit execute edit share delete manage_team
- **Matrix:** Viewer(view,audit) Executor(+execute) Editor(+edit,share) Admin(+delete,manage_team)
- **Inheritance A:** direct membership decides (override else baseline); else inherit nearest ancestor via parent_team_id; child baseline applies only to direct members; detect cycles.
- **Ownership:** team-owned resources store owned_by_team_id and authorize via effective_role(user, owned_by_team_id); never trust client-sent owner/team IDs.
- **Pipelines:** team RBAC primary; pipeline_relationships fallback only when RBAC denies. Relations: owner can_view can_execute can_edit.
- **Drafts/Jobs:** drafts.user_id user-scoped; jobs.requested_by_user_id set by server; job read requires pipeline permission.
- **Audit:** RBAC/team/share mutations + pipeline CRUD must write audit_log (actor,target,changes,request metadata).

### Implementation Mandates
Centralize authz in src/backend/rbac/* and enforce via FastAPI dependencies (no ad-hoc SQL permission checks in handlers). List endpoints: filtered results; object endpoints: 401 unauth, 403 forbidden, 404 missing. Frontend consumes backend-provided effective roles; do not reimplement permission logic client-side.

</ANCHORSKILL-RBAC-AUTHORIZATION>
