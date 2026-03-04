# Angular Test Quality Checklist

This checklist provides a standard for reviewing Angular test files to ensure stability, clarity, and maintainability. Use it during peer reviews or when auditing a test suite.

## The "So What?"
High-quality tests are the foundation of a resilient codebase. Tests that leak state, depend on execution order, or ignore accessibility aren't just technical debt — they are false signals that erode trust in the CI/CD pipeline.

---

## Test Structure

- [ ] **Fresh State per Test**: `beforeEach` creates fresh state. Variables and signals are declared at the `describe` level but initialized inside `beforeEach`.
- [ ] **Mock Cleanup**: `afterEach` includes `vi.clearAllMocks()` to prevent spy leakage between tests.
- [ ] **Logical Grouping**: Uses `describe` blocks to group related behaviors (e.g., initialization, error handling, edge cases).
- [ ] **Behavioral Naming**: Test names describe *what* the system does, not *how* (e.g., `should show error message when API fails` instead of `should call showErrorMessage() on error`).

## HTTP Tests

- [ ] **Correct Controller**: Uses `HttpTestingController` from `@angular/common/http/testing`.
- [ ] **Strict Request Verification**: Verifies the request method (`GET`, `POST`, etc.), payload body, and relevant headers.
- [ ] **Mandatory Verification**: `afterEach` includes `httpMock.verify()` to ensure no unexpected requests were made.
- [ ] **Error Path Coverage**: Specifically tests 4xx, 5xx, and network-level errors (using `req.error()`).
- [ ] **Data Factories**: Uses factory functions (e.g., `createMockUser()`) to generate test data instead of inline objects.

## Signal Tests (CRITICAL)

- [ ] **No Signal Leakage**: Signals are **never** defined/initialized at the module level or outside `beforeEach`.
- [ ] **Source Control**: Tests computed signals by manipulating their underlying source signals.
- [ ] **Effect Synchronization**: Uses `TestBed.flushEffects()` when testing logic triggered by signal effects.

## Component Tests

- [ ] **Behavioral Focus**: Tests the component through its public API and template, not by calling private methods.
- [ ] **Accessibility (A11y)**: Includes assertions for ARIA roles, labels, and focus management.
- [ ] **Mock Integration**: Uses mock services with signals (from `@testing`) to ensure component-service interactions are correctly modeled.

## Anti-Patterns to Flag

- [ ] **Signal Leakage**: Any signal or stateful variable initialized outside of `beforeEach`.
- [ ] **Zone.js Bloat**: Use of Angular `fakeAsync` or `tick`. Use Vitest's `vi.useFakeTimers()` and `vi.advanceTimersByTimeAsync()` instead.
- [ ] **Silent Failures**: `try/catch` blocks in tests that swallow errors or fail to fail the test.
- [ ] **Temporal Coupling**: Tests that depend on the execution order of other tests.
- [ ] **Weak Spies**: Spying on signal functions (e.g., `vi.spyOn(s, 'mySignal')`). Instead, control signal values through their source.

---

## Related Resources
- [HTTP Testing Patterns](examples-http-testing.md)
- [Signal Testing (Core Skill)](../SKILL.md#signal-testing-critical)
- [Mock Patterns](reference-mock-patterns.md)
