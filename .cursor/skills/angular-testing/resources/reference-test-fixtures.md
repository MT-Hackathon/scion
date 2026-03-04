# Reference: Test Fixtures

## Factory Function Patterns

Use factory functions to create consistent test data while allowing overrides for specific tests.

```typescript
export interface User {
  id: string;
  name: string;
  email: string;
  role: 'admin' | 'user';
}

export function createUser(overrides: Partial<User> = {}): User {
  return {
    id: 'user-1',
    name: 'Test User',
    email: 'test@example.com',
    role: 'user',
    ...overrides
  };
}

// Usage in tests
const admin = createUser({ role: 'admin', id: 'admin-1' });
const basicUser = createUser();
```

## Mock Data Organization

Organize mock data by entity and use a central export for shared fixtures.

```typescript
// tests/fixtures/products.ts
export const MOCK_PRODUCTS = [
  { id: 'p1', name: 'Product 1', price: 100 },
  { id: 'p2', name: 'Product 2', price: 200 },
];

// tests/fixtures/index.ts
export * from './users';
export * from './products';
```

## Fixture Loading Utilities

```typescript
/**
 * Deep clones fixture data to prevent mutation leakage between tests
 */
export function loadFixture<T>(data: T): T {
  return JSON.parse(JSON.stringify(data));
}

// In test
beforeEach(() => {
  const users = loadFixture(MOCK_USERS);
});
```

## Test Data Isolation

- Always clone data returned from factories/fixtures to prevent side effects across tests.
- Use unique identifiers for each fixture to avoid collisions.
- Clear state in `afterEach` if fixtures involve global state.

```typescript
describe('MyService', () => {
  let testData: User;

  beforeEach(() => {
    // Fresh copy for every test
    testData = createUser({ id: `user-${Math.random()}` });
  });

  afterEach(() => {
    // Cleanup if needed
  });
});
```
