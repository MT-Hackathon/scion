# Checklist: Linter Workflow

Pre-commit and during-development linter checklist for AI-assisted coding.

---

## Before Making Changes

- [ ] Check if personal config exists: `ls eslint.config.local.js`
- [ ] Note which lint command to use (`lint` vs `lint:strict`)
- [ ] Review current linter state: `npm run lint` (quick baseline)

---

## During Development

- [ ] Run linter after each significant file edit
- [ ] Fix errors immediately rather than accumulating
- [ ] Don't suppress warnings without justification
- [ ] If adding new code patterns, verify they pass lint

---

## Before Completing Task

### Required Checks

- [ ] Run full linter: `npm run lint` (or `lint:strict` if available)
- [ ] Zero errors (warnings acceptable if justified)
- [ ] No new TODO/FIXME comments added
- [ ] No magic numbers introduced
- [ ] No `any` types added
- [ ] No console.log statements

### If Warnings Exist

- [ ] Each warning has justification OR
- [ ] Warning is pre-existing (not introduced by this change)

---

## Common Fixes

### Magic Number Warning

```typescript
// Before
if (items.length > 10) { ... }

// After
const MAX_DISPLAY_ITEMS = 10;
if (items.length > MAX_DISPLAY_ITEMS) { ... }
```

### No-Console Warning

```typescript
// Before
console.log('Debug:', data);

// After - Remove or use proper logging
// For Angular, inject a logging service or remove entirely
```

### TODO/FIXME Warning

```typescript
// Before
// TODO: handle edge case

// After - Either implement or create issue
// Implemented: Added null check for edge case
```

### Explicit Any Warning

```typescript
// Before
function process(data: any) { ... }

// After
interface ProcessableData {
  id: string;
  value: number;
}
function process(data: ProcessableData) { ... }
```

---

## When to Disable Rules

**Acceptable:**

- Test files: Magic numbers in test data
- Generated code: Auto-generated files
- Third-party types: When library types are incomplete

**Not Acceptable:**

- "It's just a prototype"
- "I'll fix it later"
- "The rule is too strict"

---

## Reporting Format

When completing a task, include linter status:

**Clean:**
> Linting passed with no errors or warnings.

**With Pre-existing Issues:**
> Linting passed. 3 pre-existing warnings unrelated to this change.

**With Justified Warnings:**
> Linting complete. 1 warning (magic number in test file, acceptable per config).

**Using Strict Config:**
> Ran strict linting (magic numbers, no-console enabled). All checks passed.
