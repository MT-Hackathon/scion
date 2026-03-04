# Cross-References: Rate Limit Principles

Related skills/rules and anchors.

---

## Related Skills
- [security](../../security/SKILL.md): API authentication and credential handling
- [error-architecture](../../error-architecture/SKILL.md): Error handling patterns and exception hierarchy
- [svelte-ui](../../svelte-ui/SKILL.md): HTTP timeout and retry patterns in the frontend

## Defined Anchors
- `ANCHORSKILL-RATE-LIMITING`: Rate limit handling mandate

## Blueprints
- `blueprints/exponential-backoff.py`: `with_exponential_backoff` function
- `blueprints/circuit-breaker.py`: `CircuitBreaker` state machine class
- `blueprints/rate-limited-client.py`: `parse_rate_limit_headers`, `detect_rate_limit`, `RateLimitedApiClient`

## Key Algorithms
- **Exponential Backoff:** 1s initial, 2x multiplier, 60s max
- **Circuit Breaker:** 3 failures open, 60s cooldown, 1 success close
- **Proactive Throttle:** <10% remaining triggers delay

## HTTP Status Codes
- **429:** Too Many Requests (primary indicator)
- **503:** Service Unavailable (check Retry-After)
- **403:** Forbidden (check for quota messages)

## Headers
- `Retry-After`: Seconds to wait before retry
- `X-RateLimit-Limit`: Total requests allowed
- `X-RateLimit-Remaining`: Requests remaining
- `X-RateLimit-Reset`: Unix timestamp when limit resets
