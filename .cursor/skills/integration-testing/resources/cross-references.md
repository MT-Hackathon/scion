# Cross-References: Integration Testing

Related skills/rules and anchors.

---

## Related Skills/Rules
- [testing-debugging](../../testing-debugging/SKILL.md): Cross-layer debugging and two-attempt rule
- [data-contracts](../../data-contracts/SKILL.md): Schema validation in tests
- [error-architecture](../../error-architecture/SKILL.md): Error envelope testing
- [fullstack-workflow](../../fullstack-workflow/SKILL.md): Type alignment, integration debugging, full-stack development

## Defined Anchors
- `ANCHORSKILL-INTEGRATION-TESTING`: Integration testing mandate

## Referenced Anchors
- `ANCHORSKILL-INTEGRATION-TESTING`: Integration testing mandate (skill file)
- `ANCHORSKILL-TESTING-DEBUGGING`: Cross-layer debug protocol
- `ANCHORSKILL-FULLSTACK-WORKFLOW`: Type sync

## Test Pyramid
- **70% Unit:** Pure functions, schema validation, business logic
- **20% Integration:** HTTP handlers, backend system chains
- **10% E2E:** Full user flows (UI → HTTP → backend)

## Key Tools
- **Backend:** pytest, TestClient (FastAPI)
- **Frontend:** Vitest, Playwright (E2E)
- **Fixtures:** Shared Python/TypeScript test data
