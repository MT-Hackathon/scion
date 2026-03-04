---
name: angular-testing
description: "Governs Angular testing patterns with Vitest and TestBed: component specs, service mocks, fixture setup, and async test utilities. Use when writing, running, or debugging Angular unit tests. DO NOT use for component implementation patterns (see angular-forms-material) or cross-layer debugging (see testing-debugging)."
---

<ANCHORSKILL-ANGULAR-TESTING>

# Angular Testing

## Contents
- [Test Runner Mandate](#test-runner-mandate-critical)
- [Core Concepts & Setup](#core-concepts--setup)
- [Signal Testing](#signal-testing-critical)
- [Async & Observable Patterns](#async--observable-patterns)
- [HTTP Testing Patterns](#http-testing-patterns)
- [Infrastructure & Utilities](#infrastructure--utilities)
- [Troubleshooting](#troubleshooting)
- [Resources & Cross-References](#resources--cross-references)

## Test Runner Mandate (CRITICAL)
To ensure correct template compilation and path alias resolution, please avoid running `npx vitest` directly.
> [!CAUTION]
> **ALWAYS use `npm test` or `ng test`.** 
> The Angular builder handles Zone.js initialization, `templateUrl`/`styleUrl` compilation, and `@core/*` alias resolution.

```bash
# ✅ Recommended
npm test
npx ng test --include='**/my-feature/**/*.spec.ts'
```

## Core Concepts & Setup
- **Vitest Integration**: Use `vi.fn()` for mocks and `vi.mock()` for modules. Remember to call `vi.clearAllMocks()` in `afterEach()`.
- **TestBed**: Initialize fresh state in `beforeEach` to prevent test interference.
- **Timing**: Since we don't use Zone.js, prefer native `vi.useFakeTimers()` over Angular's `fakeAsync`/`tick`.

## Signal Testing (CRITICAL)
**Prevent State Leakage**: Always initialize signals inside `beforeEach`. Defining mutable signals at the `describe` top-level persists state across tests, causing flakiness.

```typescript
describe('SignalService', () => {
  let service: MyService;
  let isMobile: WritableSignal<boolean>;

  beforeEach(() => {
    isMobile = signal(false); // Reset for every test
    TestBed.configureTestingModule({
      providers: [
        MyService,
        { provide: MobileService, useValue: { isMobile } }
      ]
    });
    service = TestBed.inject(MyService);
  });

  afterEach(() => vi.clearAllMocks());

  it('should react to signal changes', () => {
    isMobile.set(true);
    TestBed.flushEffects(); // Critical: Force effects to execute
    expect(service.layout()).toBe('mobile');
  });
});
```

### The Reactivity Trap: Computed + FormControls
A `computed()` signal only tracks dependencies that are themselves signals. Reading `FormControl.value` (a plain property) inside a computed block fails to register a dependency, causing the value to remain "frozen" after the initial render. 

**The Fix**: Bridge the `valueChanges` observable to a signal using `toSignal()` with `startWith()`.
```typescript
searchValue = toSignal(control.valueChanges.pipe(startWith(control.value)));
characterCount = computed(() => this.searchValue()?.length ?? 0);
```
*Warning sign: UI elements or validators derived from form values work on first render but become stale after user interaction.*

For testing signal-based `input()` and `input.required()`, use `fixture.componentRef.setInput('propName', value)` instead of direct property assignment to trigger the correct reactivity internal to the component.

## Async & Observable Patterns
- **Fake Timers**: Use `await vi.advanceTimersByTimeAsync(ms)` for time-dependent logic.
- **Observables**: `async/await` with `firstValueFrom` is generally cleaner than manual subscriptions.

```typescript
it('should emit value', async () => {
  const value = await firstValueFrom(service.getData());
  expect(value).toEqual(expectedData);
});
```

## HTTP Testing Patterns
Verify the full API contract (method, URL, body) for service integrity. Include `httpMock.verify()` in `afterEach` to catch unexpected requests.

```typescript
it('should send correct POST request', () => {
  const data = { name: 'Test' };
  service.create(data).subscribe();

  const req = httpMock.expectOne('/api/resource');
  expect(req.request.method).toBe('POST');
  expect(req.request.body).toEqual(data);
  req.flush({ id: 1 });
});

afterEach(() => httpMock.verify());
```

## Infrastructure & Utilities
- **Testing Barrel**: Check `@testing` for shared mocks (`OktaAuthMockBuilder`, `createMockRouter`).
- **Data Factories**: Use `Partial<T>` overrides to quickly generate mock data without boilerplate.
```typescript
const createMockUser = (overrides: Partial<User> = {}): User => ({
  id: '1', name: 'Default', role: 'USER', ...overrides
});
```
- **Standalone Components**: Remember to import component dependencies directly into the `TestBed` configuration.

## Troubleshooting
- **NG0303 / Module Not Found**: Usually indicates the Angular builder was bypassed. Switch to `npm test`.
- **Template Resolution**: If `templateUrl` fails, use `ng test` to ensure the compiler inlines resources.
- **Signal Spying**: Control values via mocks/setters instead of `vi.spyOn`.
- **MatDialog Injector Shadowing**: Standalone components importing `MatDialogModule` create a component-level injector that shadows `TestBed` mocks. If `inject(MatDialog)` fails with `Cannot read properties of undefined (reading 'push')` or mocks are ignored, remove `MatDialogModule` from the component's `imports` array (unless template directives like `mat-dialog-title` are used).

## Resources & Cross-References
- [Service Testing](resources/examples-service-testing.md) | [Component Testing](resources/examples-component-testing.md) | [HTTP Testing](resources/examples-http-testing.md)
- [Test Quality Checklist](resources/checklist-test-quality.md) | [Mock Patterns](resources/reference-mock-patterns.md) | [TDD Templates](resources/reference-tdd-templates.md)
- [Test Fixtures](resources/reference-test-fixtures.md) | [Behavioral Testing](resources/reference-behavioral-testing.md) | [Coverage Reference](resources/reference-coverage.md)
- [E2E Testing (Playwright)](resources/examples-e2e-testing.md): Complementary end-to-end patterns; not Angular unit tests.
- [testing-debugging](../testing-debugging/SKILL.md): Universal mandates, two-attempt rule, territory principle.
- [angular-forms-material](../angular-forms-material/SKILL.md): Component implementation patterns; use for FormGroup, MatTable, and Material UI.
- [140-angular-foundation](../../rules/140-angular-foundation/RULE.mdc): Signal and component architecture.

</ANCHORSKILL-ANGULAR-TESTING>
