# Reference: Forbidden TypeScript Patterns

Patterns that MUST NOT be used in this TypeScript codebase.

---

## Forbidden Types

| Forbidden | Replacement | Reason |
|-----------|-------------|--------|
| `any` | `unknown` with type guard | Type safety |
| `Function` | Specific function signature | Type safety |
| `Object` | `object` or specific interface | Type safety |
| `{}` (empty object type) | `Record<string, unknown>` | Clarity |

---

## Forbidden Assertions

| Forbidden | Replacement | Reason |
|-----------|-------------|--------|
| `as any` | Proper typing or `unknown` | Defeats type system |
| Excessive `!` | Proper null checks | Runtime errors |
| `<Type>value` | `value as Type` | Consistency |

---

## Forbidden Patterns

### Implicit Any

```typescript
// FORBIDDEN - implicit any
function process(data) {
  return data.value;
}

// CORRECT
function process(data: { value: string }): string {
  return data.value;
}
```

### Type Assertions to Bypass Errors

```typescript
// FORBIDDEN
const user = response as any as User;

// CORRECT - validate the data
function isUser(data: unknown): data is User {
  return typeof data === 'object' && data !== null && 'id' in data;
}

if (isUser(response)) {
  const user = response;
}
```

### Non-Null Assertions Without Justification

```typescript
// FORBIDDEN
const element = document.querySelector('.item')!;
element.textContent = 'Hello';

// CORRECT
const element = document.querySelector('.item');
if (element) {
  element.textContent = 'Hello';
}
```

### Loose Equality

```typescript
// FORBIDDEN
if (value == null) { }
if (value == undefined) { }

// CORRECT
if (value === null) { }
if (value === undefined) { }
if (value == null) { } // OK only for null OR undefined check
```

### Magic Strings/Numbers

```typescript
// FORBIDDEN
if (user.role === 'admin') { }
if (timeout > 5000) { }

// CORRECT
const ROLES = {
  ADMIN: 'admin',
  USER: 'user',
} as const;

const TIMEOUT_MS = 5000;

if (user.role === ROLES.ADMIN) { }
if (timeout > TIMEOUT_MS) { }
```

### Mutable Exports

```typescript
// FORBIDDEN
export let currentUser: User;

// CORRECT
export const userService = {
  getCurrentUser(): User | null { ... }
};
```

---

## tsconfig.json Requirements

These options MUST be enabled:

```json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "strictFunctionTypes": true,
    "strictBindCallApply": true,
    "strictPropertyInitialization": true,
    "noImplicitThis": true,
    "alwaysStrict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true
  }
}
```

---

## ESLint Rules to Enforce

```json
{
  "@typescript-eslint/no-explicit-any": "error",
  "@typescript-eslint/explicit-function-return-type": "warn",
  "@typescript-eslint/no-non-null-assertion": "warn",
  "@typescript-eslint/strict-boolean-expressions": "error"
}
```
