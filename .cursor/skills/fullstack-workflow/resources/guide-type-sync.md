# Guide: Type Synchronization

How to synchronize types between TypeScript and Python.

---

## Type Mappings

| TypeScript | Python | Notes |
|------------|--------|-------|
| `string` | `str` | Exact match |
| `number` | `int` or `float` | Specify based on usage |
| `boolean` | `bool` | Exact match |
| `T \| undefined` | `Optional[T]` | Optional fields |
| `T \| null` | `T \| None` | Nullable fields |
| `string[]` | `list[str]` | Arrays |
| `Record<string, T>` | `dict[str, T]` | Objects |

## 7-Step Sync Procedure

1. Update Python data contracts (Pydantic)
2. Update TypeScript interfaces
3. Update Zod schemas
4. Run type checkers (`npm run check`, `pyright`)
5. Update tests
6. Verify integration tests
7. Document changes

## Example: Synced Types

```typescript
// Frontend (TypeScript)
interface ApiSourceConfig {
  name: string;
  url: string;
  timeout: number;
  enabled?: boolean;
}
```

```python
# Backend (Python)
class ApiSourceConfig(BaseModel):
    name: str
    url: HttpUrl
    timeout: int
    enabled: bool | None = None
```

## Validation Alignment

```typescript
// Frontend (Zod) - constraints MUST match
const schema = z.object({
  timeout: z.number().min(1).max(300)
});
```

```python
# Backend (Pydantic)
class Config(BaseModel):
    timeout: int = Field(ge=1, le=300)
```

## Detection Commands

```bash
npm run check          # TypeScript
ruff check             # Python linting
ruff format --check    # Python formatting
pyright                # Python types
```

## Common Mismatches

| Issue | Solution |
|-------|----------|
| Timestamp format | Use ISO8601 both sides |
| None vs undefined | Explicit null handling contract |
| Optional vs null | Match Optional[T] with T\|undefined |
| Enum casing | Use UPPER_SNAKE_CASE |
