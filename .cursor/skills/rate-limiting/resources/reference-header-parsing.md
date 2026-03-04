# Reference: Header Parsing

Rate limit header names and parsing logic.

**Blueprint:** `../blueprints/rate-limited-client.py` — `parse_rate_limit_headers` and `detect_rate_limit`.

---

## Standard Headers

| Header | Purpose | Example |
|--------|---------|---------|
| `X-RateLimit-Limit` | Total requests allowed | `1000` |
| `X-RateLimit-Remaining` | Requests left in window | `42` |
| `X-RateLimit-Reset` | Unix timestamp when limit resets | `1699999999` |
| `Retry-After` | Seconds to wait before retry | `60` |

---

## Detection Cascade

429 (primary) → 503 + `Retry-After` present (secondary) → 403 + quota keyword in body (tertiary).

---

## Anti-Patterns

```python
# ❌ BAD: Ignoring Retry-After header
if response.status_code == 429:
    await asyncio.sleep(1)  # Always 1 second, ignores server guidance

# ✅ GOOD: Honor Retry-After
if response.status_code == 429:
    retry_after = int(response.headers.get("Retry-After", 60))
    await asyncio.sleep(retry_after)

# ❌ BAD: Silent failure on rate limit
try:
    await api_call()
except RateLimitError:
    pass

# ✅ GOOD: Log and surface
try:
    await api_call()
except RateLimitError as err:
    logger.error("Rate limited: %s", err)
    raise
```
