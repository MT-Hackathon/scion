# Reference: Requirements Methodology

Guidelines for writing, structuring, and maintaining product requirement specifications.

---

## Document Structure

Requirements are maintained as numbered markdown files in `docs/requirements/`:

| Document | Purpose |
|----------|---------|
| `00-overview.md` | Product purpose, core capabilities, key users |
| `01-system-architecture.md` | Technology decisions, layer diagram, service topology |
| `02-data-model.md` | Database schema, entity relationships, constraints |
| `03-roles-permissions.md` | Role definitions, permission matrix, row-level access |
| `04-workflow-lifecycle.md` | State machine, transitions, approval gates, side effects |
| `05-api-specification.md` | Endpoint inventory, request/response contracts, error formats |
| `06-frontend-application.md` | Route map, component hierarchy, form patterns |
| `07-security-identity.md` | Authentication flow, authorization model, identity types |
| `08-rules-engine.md` | Rule domains, condition model, evaluation, simulation |
| `09-configuration-admin.md` | Display names, entity config, delegation, audit |
| `10-deployment-infrastructure.md` | Local setup, builds, CI/CD, containers |
| `11-future-roadmap.md` | Known gaps, planned features, technical debt |
| `12-feature-interaction-map.md` | User journeys, acceptance criteria, end-to-end flows, implementation completeness |

---

## Section Guidelines

### 00 — Product Overview
- **Purpose**: 3-5 sentences on what the system does and why it exists
- **Core Capabilities**: Table with numbered capabilities, each with one-sentence description
- **Key Users**: Table mapping roles to personas and primary actions
- **Scope Boundaries**: What the system does NOT do (prevents scope creep)

### 01 — System Architecture
- Technology decisions table: Layer | Technology | Rationale
- Architecture diagram showing all layers (frontend, backend, database, SSO)
- Integration points (Okta, SABHRS, rules engine)

### 02 — Data Model
- Entity definitions with column types, constraints, and defaults
- Use PostgreSQL conventions: UUID PKs, `TIMESTAMPTZ`, enums for statuses
- Relationship diagrams (FK references, cascade rules)
- Index definitions for performance-critical queries

### 03 — Roles & Permissions
- Role inventory with scope (agency-scoped vs global)
- Permission vocabulary (domain-organized)
- Permission matrix: Permission x Role -> Allow/Deny
- Row-level access rules (who sees what data)

### 04 — Workflow Lifecycle
- State definitions with entry/exit criteria
- Transition map: `from_state -> action -> to_state`
- Role permissions per transition
- Side effects (notifications, audit entries, status changes)
- Approval gate triggers and resolution

### 05 — API Specification
- Endpoints grouped by resource domain
- For each endpoint: Method, Path, Auth Required, Permissions, Request DTO, Response DTO
- Error response format (RFC 7807 Problem Detail)
- Pagination, filtering, and sorting patterns

### 06 — Frontend Application
- Route map with all pages, layouts, and access requirements
- Component organization (core / shared / features)
- Form patterns and validation rules
- State management approach (signals, services)

### 07 — Security & Identity
- Authentication flow (end-to-end, step by step)
- Identity types and normalization rules
- Authorization enforcement layers (API, route, UI)
- Session management and token lifecycle

### 12 — Feature Interaction Map
- **Purpose**: The human interaction paradigm — maps every capability to user journeys
- **Feature Cards**: Each of the 14 core capabilities gets a Feature Card with: Actors, Entry Points, User Journey, Screen Inventory, Success Criteria, Acceptance Tests, Dependencies, Implementation Status
- **Acceptance Tests**: Given/When/Then format covering happy path, error path, permission denial, edge cases
- **End-to-End Flows**: Cross-feature scenarios (A through D) that verify the system works as a whole
- **Implementation Completeness Matrix**: Tracks backend/frontend/tests/e2e status for all 14 features
- **Gap Summary**: Prioritized list of missing capabilities (Critical, High, Medium, Low)
- **Cross-reference**: [Product Management Skill](../../product-management/SKILL.md) for scripts and checklists

---

## Writing Principles

1. **Concrete, not abstract**: Include actual column names, endpoint paths, and status codes -- not vague descriptions
2. **Copy-paste verifiable**: Every constraint, rule, or behavior should be testable from the description alone
3. **Non-ambiguous**: Specify exact types, field lengths, defaults, and constraints. "A string field" is insufficient; "VARCHAR(255) NOT NULL DEFAULT 'DRAFT'" is correct
4. **Audience-aware**: Technical enough for developers implementing features, structured enough for stakeholders reviewing scope
5. **Version-controlled**: Include document date in header. Use git history for change tracking
6. **Consistent terminology**: Use the same term for the same concept across all documents (e.g., always "purchasing agency" not sometimes "owning agency")

---

## When to Update Requirements

| Trigger | Action |
|---------|--------|
| New feature planned | Add to relevant section(s) BEFORE implementation |
| Implementation reveals gap | Update document to match actual behavior |
| Business rule change | Update workflow, permissions, or API spec as needed |
| Schema change | Update data model document in same commit as migration |
| Security model change | Update security-identity document |

---

## Quality Checklist

- [ ] Every table referenced in code has a definition in `02-data-model.md`
- [ ] Every API endpoint has a row in `05-api-specification.md`
- [ ] Every role has permissions defined in `03-roles-permissions.md`
- [ ] Every workflow state has transitions defined in `04-workflow-lifecycle.md`
- [ ] Every route has an entry in `06-frontend-application.md`
- [ ] Every core capability has a Feature Card in `12-feature-interaction-map.md`
- [ ] Every Feature Card has acceptance tests in Given/When/Then format
- [ ] Implementation Completeness Matrix is up to date
- [ ] Terminology is consistent across all documents
- [ ] No TODOs or placeholder text remaining
