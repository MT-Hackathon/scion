---
name: fullstack-workflow
description: "Governs full-stack workflow for backend-UI integration, type synchronization, and cross-stack debugging. Use when planning work spanning both backend and frontend, modifying shared types, or diagnosing integration failures. DO NOT use for backend-only changes (see java-spring-boot, api-design) or frontend-only work (see svelte-ui)."
---

<ANCHORSKILL-FULLSTACK-WORKFLOW>

# Full-Stack Workflow Rule

## Resources
- [Core Concepts](#core-concepts)
- [Guide: Type Sync](resources/guide-type-sync.md)
- [Guide: Cross-Stack Debugging](resources/guide-cross-stack-debugging.md)
- [Cross-References](resources/cross-references.md)
- For dev server startup, see the [dev-startup skill](../dev-startup/SKILL.md).

## Core Concepts

### Where to Start (MANDATED)
- Start **backend-first** for schema/API/pipeline changes
- Start **frontend-first** for UX/styling only
- Start on **both** for new node types, API contracts, or execution flows

### Type Synchronization (MANDATED)
TypeScript and Python types MUST align for node schemas, HTTP contracts, validation:
- **Field names:** Exact match, snake_case for data
- **Types:** Optional[T] ↔ T|undefined, string ↔ str, number ↔ int
- **Validation:** Min/max, patterns, required/optional, defaults match

### Collection Pagination (MANDATED)
All collection/list endpoints MUST support explicit pagination.
- Request params: `page`, `size`, optional `sort`
- Server enforces bounded `size` (default + hard maximum) and rejects or clamps values above max
- Responses include pagination metadata (`page`, `size`, `total`) so clients can request subsequent pages deterministically

### Cross-Stack Debugging
Identify boundary first: UI rendering → UI bug; HTTP unreachable → network bug; No response → backend bug; Wrong structure → type mismatch

### Coordination Rules
- Never build frontend features depending on missing backend contracts
- Every contract change must update backend models, frontend types, and tests
- Sync on `VITE_API_URL`, CORS allowances, and error envelopes

### Forbidden Patterns
- Frontend work without backend types/schemas
- Breaking changes without migration/documentation
- Updating only one side of type contracts
- Testing without reproducing, guessing boundaries

</ANCHORSKILL-FULLSTACK-WORKFLOW>
