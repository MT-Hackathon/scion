# Examples: TypeScript Type Patterns

Type patterns for strict TypeScript development.

---

## Prefer Type Inference

```typescript
// GOOD - inference is obvious
const count = 0;
const name = 'John';
const items = ['a', 'b', 'c'];

// GOOD - explicit for complex types
const config: AppConfig = {
  apiUrl: '/api',
  timeout: 5000,
};

// GOOD - explicit for function parameters
function processUser(user: User): void {
  // ...
}
```

---

## Use Unknown Instead of Any

```typescript
// BAD
function parseData(data: any): User {
  return data as User;
}

// GOOD - use unknown with type guard
function parseData(data: unknown): User {
  if (isUser(data)) {
    return data;
  }
  throw new Error('Invalid user data');
}

function isUser(data: unknown): data is User {
  return (
    typeof data === 'object' &&
    data !== null &&
    'id' in data &&
    'name' in data
  );
}
```

---

## Generic Types

```typescript
// GOOD - generic for flexibility
function first<T>(items: T[]): T | undefined {
  return items[0];
}

// GOOD - constrained generic
function getProperty<T, K extends keyof T>(obj: T, key: K): T[K] {
  return obj[key];
}

// GOOD - generic interface
interface ApiResponse<T> {
  data: T;
  status: number;
  message: string;
}
```

---

## Readonly Patterns

```typescript
// GOOD - readonly for immutable properties
interface User {
  readonly id: string;
  readonly createdAt: Date;
  name: string; // mutable
}

// GOOD - readonly arrays
function processItems(items: readonly string[]): void {
  // items.push('x'); // Error - cannot modify
}

// GOOD - as const for literals
const ROLES = ['admin', 'user', 'guest'] as const;
type Role = typeof ROLES[number]; // 'admin' | 'user' | 'guest'
```

---

## Null Safety

```typescript
// GOOD - optional chaining
const userName = user?.profile?.name;

// GOOD - nullish coalescing
const displayName = userName ?? 'Anonymous';

// GOOD - explicit null handling
function getUser(id: string): User | null {
  const user = users.find(u => u.id === id);
  return user ?? null;
}

// AVOID - non-null assertion (use sparingly)
const element = document.getElementById('app')!;

// BETTER - with guard
const element = document.getElementById('app');
if (!element) {
  throw new Error('App element not found');
}
```

---

## Union and Intersection Types

```typescript
// Union type
type Status = 'pending' | 'active' | 'completed';

// Discriminated union
interface LoadingState {
  status: 'loading';
}

interface SuccessState {
  status: 'success';
  data: User[];
}

interface ErrorState {
  status: 'error';
  error: string;
}

type State = LoadingState | SuccessState | ErrorState;

// Type narrowing
function handleState(state: State): void {
  switch (state.status) {
    case 'loading':
      showSpinner();
      break;
    case 'success':
      renderUsers(state.data); // TypeScript knows data exists
      break;
    case 'error':
      showError(state.error); // TypeScript knows error exists
      break;
  }
}
```

---

## Import Organization

```typescript
// 1. Angular core
import {Component, inject, signal} from '@angular/core';
import {CommonModule} from '@angular/common';

// 2. Third-party
import {MatButtonModule} from '@angular/material/button';
import {OKTA_AUTH} from '@okta/okta-angular';

// 3. Project aliases
import {UserService} from '@core/services/user.service';
import {environment} from '@env/environment';

// 4. Relative
import {UserCard} from './user-card.component';
```

---

## Interface vs Type

```typescript
// Use interface for object shapes (extendable)
interface User {
  id: string;
  name: string;
}

interface Admin extends User {
  permissions: string[];
}

// Use type for unions, primitives, tuples
type Status = 'active' | 'inactive';
type Coordinates = [number, number];
type StringOrNumber = string | number;

// Use type for mapped/conditional types
type Readonly<T> = {
  readonly [P in keyof T]: T[P];
};
```
