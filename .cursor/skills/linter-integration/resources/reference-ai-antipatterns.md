# Reference: AI Anti-Patterns

Lintable code smells commonly produced by AI that should be caught automatically.

---

## TypeScript/JavaScript (ESLint)

### Magic Numbers

AI frequently generates unexplained numeric literals.

```typescript
// BAD - AI-generated
if (retryCount > 3) { ... }
setTimeout(callback, 5000);
const pageSize = 50;

// GOOD - With constants
const MAX_RETRIES = 3;
const TIMEOUT_MS = 5000;
const DEFAULT_PAGE_SIZE = 50;

if (retryCount > MAX_RETRIES) { ... }
setTimeout(callback, TIMEOUT_MS);
```

**ESLint Rule:**

```javascript
'@typescript-eslint/no-magic-numbers': ['warn', {
  ignore: [0, 1, -1, 2, 10],  // Common safe values
  ignoreEnums: true,
  ignoreNumericLiteralTypes: true,
  enforceConst: true,
  ignoreReadonlyClassProperties: true
}]
```

---

### TODO/FIXME Comments

AI often leaves placeholder comments that get forgotten.

```typescript
// BAD
// TODO: implement error handling
// FIXME: this needs optimization
// HACK: temporary workaround

// GOOD - Either implement or remove
```

**ESLint Rule:**

```javascript
'no-warning-comments': ['warn', { 
  terms: ['TODO', 'FIXME', 'HACK', 'XXX', 'BUG'],
  location: 'start'
}]
```

---

### Explicit Any Type

AI uses `any` to bypass type checking when uncertain.

```typescript
// BAD
function processData(data: any): any { ... }
const result = response as any;

// GOOD
function processData(data: unknown): ProcessedData { ... }
function isValidData(data: unknown): data is ValidData { ... }
```

**ESLint Rule:**

```javascript
'@typescript-eslint/no-explicit-any': 'error'
```

---

### Console Statements

AI includes debug logging that shouldn't ship.

```typescript
// BAD
console.log('debugging:', data);
console.error(error);

// GOOD - Use proper logging
this.logger.debug('Processing data', { data });
this.logger.error('Operation failed', { error });
```

**ESLint Rule:**

```javascript
'no-console': 'warn'
```

---

### Non-Null Assertions

AI uses `!` to silence TypeScript without proper checks.

```typescript
// BAD
const element = document.querySelector('.item')!;
const user = this.users.find(u => u.id === id)!;

// GOOD
const element = document.querySelector('.item');
if (!element) throw new Error('Element not found');

const user = this.users.find(u => u.id === id);
if (!user) throw new Error(`User ${id} not found`);
```

**ESLint Rule:**

```javascript
'@typescript-eslint/no-non-null-assertion': 'warn'
```

---

## Python (Ruff)

### Print Statements

```python
# BAD
print(f"Debug: {data}")

# GOOD
logger.debug("Processing data", extra={"data": data})
```

**Ruff Rule:** `T201` (flake8-print)

---

### Unused Variables

```python
# BAD
result = expensive_operation()  # never used
for item in items:
    unused = process(item)  # assigned but not used

# GOOD
_ = expensive_operation()  # Explicit discard
for item in items:
    process(item)  # No assignment if not needed
```

**Ruff Rule:** `F841` (Pyflakes)

---

### Bare Except

```python
# BAD
try:
    risky_operation()
except:
    pass

# GOOD
try:
    risky_operation()
except SpecificError as e:
    logger.error("Operation failed", exc_info=e)
    raise
```

**Ruff Rule:** `E722` (pycodestyle)

---

## Angular-Specific

### Old Structural Directives

AI trained on older Angular may generate deprecated patterns.

```html
<!-- BAD - Old syntax -->
<div *ngIf="condition">...</div>
<div *ngFor="let item of items">...</div>

<!-- GOOD - Angular 21+ control flow -->
@if (condition) {
  <div>...</div>
}
@for (item of items; track item.id) {
  <div>...</div>
}
```

**Detection:** Custom ESLint rule or template linting

---

### Decorator-Based Input/Output

```typescript
// BAD - Old pattern
@Input() value: string;
@Output() valueChange = new EventEmitter<string>();

// GOOD - Angular 21+ signals
value = input<string>();
valueChange = output<string>();
```

---

## Recommended Strict Config

### ESLint (TypeScript/Angular)

```javascript
{
  '@typescript-eslint/no-magic-numbers': ['warn', {
    ignore: [0, 1, -1, 2, 10],
    ignoreEnums: true,
    enforceConst: true
  }],
  '@typescript-eslint/no-explicit-any': 'error',
  '@typescript-eslint/no-non-null-assertion': 'warn',
  'no-console': 'warn',
  'no-warning-comments': ['warn', { terms: ['TODO', 'FIXME', 'HACK'] }],
  'no-unused-vars': 'off',
  '@typescript-eslint/no-unused-vars': ['error', {
    argsIgnorePattern: '^_',
    varsIgnorePattern: '^_'
  }]
}
```

### Ruff (Python)

```toml
[lint]
select = [
  "E",      # pycodestyle errors
  "W",      # pycodestyle warnings
  "F",      # Pyflakes
  "I",      # isort
  "B",      # flake8-bugbear
  "T20",    # flake8-print
  "SIM",    # flake8-simplify
  "RUF",    # Ruff-specific
]
```
