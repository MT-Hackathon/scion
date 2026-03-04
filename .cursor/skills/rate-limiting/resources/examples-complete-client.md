# Examples: Complete Client

Full `RateLimitedApiClient` integration pattern.

**Blueprint:** `../blueprints/rate-limited-client.py` — `RateLimitedApiClient` class plus
`parse_rate_limit_headers` and `detect_rate_limit` utilities.

---

## Components Used

| Component | Blueprint | Purpose |
|-----------|-----------|---------|
| `CircuitBreaker` | circuit-breaker.py | Fail fast when API unavailable |
| `with_exponential_backoff` | exponential-backoff.py | Retry with increasing delays |
| `parse_rate_limit_headers` | rate-limited-client.py | Extract rate info from response |
| `detect_rate_limit` | rate-limited-client.py | Identify rate limit responses |

---

## Usage

```python
client = RateLimitedApiClient("https://api.example.com")  # ILLUSTRATIVE

try:
    data = await client.get("/users")
except CircuitBreakerOpenError:
    logger.error("API circuit breaker open")
except RateLimitError:
    logger.error("Rate limit retries exhausted")
```
