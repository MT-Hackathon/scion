# Checklist: Testing & Debugging

Validation steps for testing and debugging.

---

## Testing Checklist

- [ ] Every public function has ≥1 unit test
- [ ] Tests encode business rules, not framework wiring
- [ ] Each test name reads as an acceptance criterion a stakeholder would recognize
- [ ] Coverage reflects tested business logic, not tested boilerplate
- [ ] Edge cases tested (empty, None, max values)
- [ ] Core modules have ≥90% test coverage
- [ ] Tests use descriptive names
- [ ] No try-except skip/pass in tests
- [ ] Assertions are strict (no lowering quality to pass)
- [ ] Tests written AFTER understanding requirements

## Backend Debug Checklist

- [ ] Logging added for diagnostic context
- [ ] Unit test reproduces bug
- [ ] Stack trace captured
- [ ] Code fix implemented
- [ ] Test passes after fix
- [ ] No workarounds or quick fixes

## UI Debug Checklist

- [ ] Page navigation verified
- [ ] Page snapshot captured
- [ ] Console errors checked
- [ ] Network requests inspected
- [ ] User interaction tested
- [ ] Component code reviewed
- [ ] Fix implemented
- [ ] BEFORE/AFTER screenshots taken
- [ ] State differences documented
- [ ] Re-test performed

## Test Failure Diagnostic Checklist

- [ ] Test validity checked first
- [ ] Environment verified (uv/node)
- [ ] Configuration validated
- [ ] Test infrastructure working
- [ ] Code investigation last (after above)
