# Checklist: Integration Testing

Integration testing validation checklist.

---

## Test Pyramid Compliance

- [ ] ~70% unit tests (pure functions, validation)
- [ ] ~20% integration tests (HTTP handlers, backend chains)
- [ ] ~10% E2E tests (full user flows)
- [ ] Unit tests written before integration tests
- [ ] Integration tests written before E2E tests

## Integration Test Coverage

- [ ] Success paths tested for all handlers
- [ ] Invalid arguments tested
- [ ] Missing arguments tested
- [ ] Malformed JSON tested
- [ ] Timeout paths tested
- [ ] Error codes verified

## HTTP Flow Testing

- [ ] Request/response envelope format validated
- [ ] Success responses have `success: true` and `data`
- [ ] Error responses have `success: false` and `error`
- [ ] Error codes match documented codes
- [ ] Timeout handling tested (<30s)

## Shared Fixtures

- [ ] Fixtures defined in `tests/fixtures/`
- [ ] Same fixtures used by frontend and backend tests
- [ ] Fixtures valid against both Zod and Pydantic
- [ ] Invalid fixtures test all edge cases
- [ ] Fixtures documented with comments

## Manual Validation Steps

- [ ] Launch app successfully
- [ ] Sidecar ping responds
- [ ] Create new pipeline in UI
- [ ] Save pipeline to backend
- [ ] Load pipeline from backend
- [ ] Execute pipeline
- [ ] Verify status updates
- [ ] Verify error display

## Forbidden Patterns

- [ ] No integration tests without unit coverage
- [ ] No divergent fixtures between frontend/backend
- [ ] No flaky tests (manual sleeps, timing assumptions)
- [ ] No E2E tests without integration coverage
- [ ] No skipped tests without justification

## Test Organization

- [ ] Unit tests in `tests/unit/`
- [ ] Integration tests in `tests/integration/`
- [ ] E2E tests in `tests/e2e/`
- [ ] Fixtures in `tests/fixtures/`
- [ ] Test files named `test_*.py` or `*.test.ts`
