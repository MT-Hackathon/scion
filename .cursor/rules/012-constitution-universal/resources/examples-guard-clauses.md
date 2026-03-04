# Examples: Guard Clauses

Guard clause patterns that apply across all languages.

---

## Pattern

Guard clauses validate inputs and preconditions at function start, returning early for invalid cases.

### Good: Early Returns

```python
def process_user(user_id: str, data: dict) -> Result:
    if not user_id:
        return Error("user_id required")
    if not data:
        return Error("data required")
    if not validate_user_exists(user_id):
        return Error("user not found")
    
    # Single success path
    return process_valid_user(user_id, data)
```

```typescript
function processUser(userId: string, data: Record<string, unknown>): Result {
    if (!userId) return { error: "userId required" };
    if (!data) return { error: "data required" };
    if (!validateUserExists(userId)) return { error: "user not found" };
    
    // Single success path
    return processValidUser(userId, data);
}
```

### Bad: Nested Conditions

```python
# AVOID: Deep nesting
def process_user(user_id, data):
    if user_id:
        if data:
            if validate_user_exists(user_id):
                return process_valid_user(user_id, data)
            else:
                return Error("user not found")
        else:
            return Error("data required")
    else:
        return Error("user_id required")
```

---

## Key Principles

1. **Fail fast**: Check invalid conditions first
2. **One success path**: Main logic at the end, unindented
3. **Max 3 nesting**: If deeper, refactor
4. **2+ guards minimum**: Significant functions should validate inputs
