# Examples: Angular Test Patterns

Testing patterns for Angular with Vitest and TestBed.

For detailed patterns, see [angular-testing](../../angular-testing/SKILL.md).

---

## Basic Test Structure

```typescript
import {TestBed} from '@angular/core/testing';
import {describe, it, expect, beforeEach, afterEach, vi} from 'vitest';

describe('MyService', () => {
  let service: MyService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [MyService],
    });
    service = TestBed.inject(MyService);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
```

---

## UI Debug Workflow

```
1. Bug reported: "Save button doesn't work"
2. Open browser DevTools
3. Check Console tab for errors
4. Check Network tab for failed requests
5. Click button, observe interaction
6. Read component code in src/app/
7. Fix code
8. Screenshot BEFORE vs AFTER (required)
9. Run: npm test
10. Verify fix
```

---

## Test Failure Diagnostic Order

```
Test fails: navigation.service.spec.ts
↓
1. Check test validity: Is assertion correct?
   → Yes, expects isNavigationOpen() to be true
↓
2. Check environment: Node activated?
   → Run: node --version (should be 22.x)
   → Run: npm install (dependencies up to date?)
↓
3. Check configuration: TestBed configured?
   → Providers correct? Mocks created?
↓
4. Check test infrastructure: Vitest working?
   → Run: npm test -- --run
↓
5. NOW investigate code bug
```

---

## Common Vitest Assertions

```typescript
// Truthiness
expect(service).toBeTruthy();
expect(result).toBeFalsy();

// Equality
expect(value).toBe(5);
expect(obj).toEqual({id: 1, name: 'test'});

// Arrays
expect(items.length).toBe(3);
expect(items).toContain('expected');

// Mocks
expect(mockFn).toHaveBeenCalled();
expect(mockFn).toHaveBeenCalledWith('arg1', 'arg2');
expect(mockFn).toHaveBeenCalledTimes(2);
```

---

## Running Tests

**ALWAYS use `npm test --` to run tests.** Never invoke `vitest` directly—Angular's builder handles path alias resolution (`@core/*` → `src/app/core/*`).

```bash
# Run all tests
npm test

# Run tests once (no watch)
npm test -- --run

# Run specific test file
npm test -- navigation.service

# Run with coverage
npm test -- --coverage
```

**Anti-pattern**: `npx vitest run src/app/foo.spec.ts` — bypasses Angular's build pipeline, causing path alias resolution failures.
