# Examples: Error Mapping

Error handling patterns across layers.

---

## Error Envelope

```typescript
interface ErrorResponse {
  status: "error";
  error: {
    code: string;
    message: string;
  };
  details?: unknown;
  id?: string;
}
```

---

## Backend Error Mapping

```python
# Keyed by exception type; static messages only — dynamic messages fall back to str(err)
_ERROR_CODES: dict[type, str] = {
    ValidationError: "VALIDATION_ERROR",
    TimeoutError:    "TIMEOUT",
    RateLimitError:  "RATE_LIMIT_EXCEEDED",
}
_ERROR_MESSAGES: dict[str, str] = {
    "TIMEOUT":            "Operation timed out",
    "RATE_LIMIT_EXCEEDED": "Rate limit exceeded. Retry later.",
}

def map_exception_to_error(err: Exception) -> dict:
    """Map Python exception to error envelope."""
    code = _ERROR_CODES.get(type(err))
    if code is None:
        logger.error(f"Unexpected error: {err}", exc_info=True)
        return {"status": "error", "error": {"code": "UNKNOWN_ERROR", "message": "An unexpected error occurred"}}
    message = _ERROR_MESSAGES.get(code, str(err))
    return {"status": "error", "error": {"code": code, "message": message}}
```

---

## Frontend Error Display

```svelte
<script lang="ts">
function handleError(error: ErrorResponse) {
  const severity = getSeverity(error.error.code);
  
  switch (severity) {
    case 'info':
      showToast(error.error.message);
      break;
    case 'warning':
      showInlineError(error.error.message);
      break;
    case 'error':
      showModal(error.error.message);
      break;
    case 'critical':
      showBanner(error.error.message);
      break;
  }
}

function getSeverity(code: string): 'info' | 'warning' | 'error' | 'critical' {
  if (code === 'VALIDATION_ERROR') return 'warning';
  if (code === 'TIMEOUT') return 'warning';
  if (code === 'CONNECTION_FAILED') return 'critical';
  if (code === 'UNAUTHORIZED') return 'error';
  return 'error';
}
</script>
```
