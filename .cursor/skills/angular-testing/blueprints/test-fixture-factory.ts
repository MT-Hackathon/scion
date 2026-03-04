// BLUEPRINT: test-fixture-factory.ts
// STRUCTURAL: Factory pattern, deep-clone utility, central fixture barrel
// ILLUSTRATIVE: Entity types, field names, default values — replace with your domain model

// STRUCTURAL: Deep clone prevents mutation leakage between tests.
// Always call loadFixture() when sharing constant arrays; never share references.
export function loadFixture<T>(data: T): T {
  return JSON.parse(JSON.stringify(data));
}

// ILLUSTRATIVE: Replace with your entity interface.
export interface User {
  id: string;
  name: string;
  email: string;
  role: 'admin' | 'user';
}

// STRUCTURAL: Factory function with Partial<T> overrides.
// Copy this pattern for every domain entity in your test suite.
export function createUser(overrides: Partial<User> = {}): User {
  return {
    id: 'user-1',
    name: 'Test User',
    email: 'test@example.com',
    role: 'user',
    ...overrides,
  };
}

// ILLUSTRATIVE: Replace with your entity and fields.
// STRUCTURAL: Constant arrays stay immutable; clone before any mutation.
export const MOCK_PRODUCTS = [
  { id: 'p-1', name: 'Product One', price: 100 },
  { id: 'p-2', name: 'Product Two', price: 200 },
] as const;

// STRUCTURAL: Central barrel — re-export all fixture modules from one index.
// tests/fixtures/index.ts:
//   export * from './users';
//   export * from './products';

// Usage:
//   const admin = createUser({ role: 'admin', id: 'admin-1' });
//   const products = loadFixture(MOCK_PRODUCTS);  // always clone before mutating
//
//   describe('MyService', () => {
//     let testUser: User;
//     beforeEach(() => {
//       testUser = createUser({ id: `user-${Math.random()}` });
//     });
//   });
