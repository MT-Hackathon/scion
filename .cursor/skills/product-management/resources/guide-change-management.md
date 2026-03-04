# Guide: Requirements Change Management

How to handle changes to requirements — whether new features, scope changes, or gaps discovered during implementation.

---

## When Requirements Change

| Change Type | Action |
|-------------|--------|
| New feature | Create Feature Card in doc 12 BEFORE implementation |
| Modified acceptance criteria | Update Feature Card, assess impact on existing tests |
| Removed feature | Mark Feature Card as deprecated, remove from matrix |
| Scope reduction | Update success criteria to reflect new scope |
| Priority change | Update Gap Summary section in doc 12 |

---

## When Implementation Reveals Gaps

1. If implementation shows the requirement is incomplete, update doc 12 FIRST
2. If a dependency is missing, escalate to PM before working around it
3. Never implement against an ambiguous requirement — clarify first

---

## Minimum Test Coverage Per Feature

Every feature must have acceptance criteria covering at minimum:

| Scenario Type | Required |
|---------------|----------|
| Happy path (primary user journey succeeds) | Yes |
| Validation failure (required field missing) | Yes |
| Permission denial (unauthorized access) | Yes |
| Error handling (server error, timeout) | Yes |
| Edge case (boundary values, concurrent actions) | If applicable |

For detailed scenario templates by feature type, see [Acceptance Criteria Template](template-acceptance-criteria.md).
