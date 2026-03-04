# Examples: Exponential Backoff

Retry with exponential backoff implementation pattern.

**Blueprint:** `../blueprints/exponential-backoff.py` — `with_exponential_backoff` function.

---

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| initial_delay | 1.0s | First retry delay |
| max_delay | 60.0s | Maximum delay cap |
| multiplier | 2.0 | Delay multiplier per attempt |
| max_retries | 5 | Maximum retry attempts |

---

## Anti-Patterns

```python
# ❌ BAD: Immediate retry without backoff
try:
    result = await api_call()
except RateLimitError:
    result = await api_call()

# ✅ GOOD: Exponential backoff via with_exponential_backoff()

# ❌ BAD: No max backoff cap
delay = 1
while True:
    delay *= 2  # Grows without bound
    await asyncio.sleep(delay)

# ✅ GOOD: Cap maximum backoff
delay = min(delay * 2, 60)
```
