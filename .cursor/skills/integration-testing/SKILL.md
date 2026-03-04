---
name: integration-testing
description: "Provides end-to-end testing strategy for backend-UI integration flows: API contract testing, service integration, test containers, and cross-layer scenario coverage. Use when implementing integration tests, validating API endpoints end-to-end, or testing service interactions. DO NOT use for unit testing (see angular-testing) or debugging test failures (see testing-debugging)."
---

<ANCHORSKILL-INTEGRATION-TESTING>

# Integration Testing Rule

## Table of Contents & Resources
- [Core Concepts](#core-concepts)
- [Examples: Test Pyramid](resources/examples-test-pyramid.md)
- [Examples: HTTP Flow Testing](resources/examples-http-flow-testing.md)
- [Reference: Shared Fixtures](resources/reference-shared-fixtures.md)
- [Checklist: Integration Testing](resources/checklist-integration-testing.md)
- [Cross-References](resources/cross-references.md)
- [Blueprint: Python Fixtures](blueprints/pytest-integration-fixtures.py)
- [Blueprint: TypeScript Fixtures](blueprints/ts-integration-fixtures.ts)

## Core Concepts

### Test Pyramid (MANDATED)
- **Unit:** ~70% of tests (pure functions, schema checks).
- **Integration:** ~20% (HTTP handlers, backend system chains).
- **E2E:** ~10% (UI → HTTP → backend → response).
- Always add unit tests before integration or E2E tests.

### Required Integration Coverage
- Backend handlers: success, invalid/missing args, malformed JSON, timeout paths.
- HTTP flows: request/response envelope, error codes, and timeouts.
- Fixtures: shared data models valid against both Pydantic and Zod.

### Manual Validation
- Launch app, confirm sidecar ping.
- Create/save/load a pipeline.
- Execute and verify status + error display.

### Forbidden Patterns
- Integration/E2E tests without unit coverage.
- Divergent fixtures between frontend and backend.
- Flaky tests requiring manual sleeps or timing hacks.

</ANCHORSKILL-INTEGRATION-TESTING>
