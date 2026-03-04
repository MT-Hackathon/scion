# Guide: Cross-Stack Debugging

Procedures for debugging issues spanning frontend, HTTP, and backend layers.

---

## Boundary Identification (MANDATED)

```
UI rendering issue → Check browser console/network → UI bug
HTTP unreachable  → Check curl, ports, CORS     → Network bug
No response       → Check backend logs, FastAPI → Backend bug
Wrong structure   → Check type sync, contracts  → Type mismatch
```

## Debugging Flow

1. Reproduce issue consistently
2. Identify boundary (UI/HTTP/Backend)
3. Isolate layer with targeted tests
4. Fix root cause (not symptoms)
5. Add regression test

## Tools by Layer

| Layer | Tools |
|-------|-------|
| Frontend | Browser snapshot/console, SvelteKit dev logs |
| HTTP | curl, Postman, fetch helper tests |
| Backend | pytest, uvicorn logs, data store inspection |

## Quick Checks

```bash
# Kill stuck servers
lsof -ti:4173 | xargs kill -9  # Frontend
lsof -ti:8000 | xargs kill -9  # Backend

# Verify backend
curl http://localhost:8000/health
curl -s http://localhost:8000/api/pipelines | jq
```

## Common Bug Patterns

| Pattern | Symptoms | Solution |
|---------|----------|----------|
| Serialization | NaN→null, undefined omitted | Validate before json.dumps() |
| Timeout | Frontend timeout, backend processing | Use async job pattern |
| Validation Mismatch | Form submits but backend rejects | Align Zod + Pydantic |
| Case Sensitivity | Fields not parsed | Use snake_case for HTTP |
| Null vs Undefined | Optional fields differ | Explicit null contract |
| Race Conditions | Stale data, out-of-order | Use AbortController |

## Serialization Fix

```python
import math

def sanitize_for_json(obj):
    if isinstance(obj, float):
        if math.isnan(obj): return None
        if math.isinf(obj): return 1e10 if obj > 0 else -1e10
    return obj
```

## Race Condition Fix

```typescript
let controller: AbortController | null = null;

async function fetchData(query: string) {
  controller?.abort();
  controller = new AbortController();
  
  try {
    const response = await fetch(`/api/search?q=${query}`, {
      signal: controller.signal
    });
    return await response.json();
  } catch (e) {
    if (e.name === 'AbortError') return null;
    throw e;
  }
}
```

## Testing Strategy

- **Isolated first:** `pytest tests/unit/`, `npm run test` (mocked)
- **Integrated when needed:** Start both servers, exercise HTTP flows
