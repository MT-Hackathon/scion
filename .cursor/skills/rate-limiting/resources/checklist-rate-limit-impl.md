# Checklist: Rate Limit Implementation

Rate limit handling validation checklist.

---

## Exponential Backoff

- [ ] Initial delay: 1 second
- [ ] Multiplier: 2x per attempt
- [ ] Maximum delay: 60 seconds
- [ ] Backoff resets on success
- [ ] Max retry attempts defined (e.g., 5)

## Header Parsing

- [ ] Parse `Retry-After` header
- [ ] Parse `X-RateLimit-Limit` (total quota)
- [ ] Parse `X-RateLimit-Remaining` (requests left)
- [ ] Parse `X-RateLimit-Reset` (reset timestamp)
- [ ] Log all rate limit headers for debugging

## Proactive Throttling

- [ ] Check `X-RateLimit-Remaining` before requests
- [ ] Throttle when remaining <10% of limit
- [ ] Implement request queuing if needed
- [ ] Warn user when approaching rate limit

## Circuit Breaker

- [ ] Open after 3 consecutive 429 responses
- [ ] Cooldown period: 60 seconds
- [ ] Half-open state for testing recovery
- [ ] Close after 1 successful request in half-open
- [ ] Log circuit state changes

## Detection

- [ ] Detect 429 status (primary indicator)
- [ ] Detect 503 with `Retry-After` header
- [ ] Detect 403 with quota exhaustion message
- [ ] Check response body for rate limit keywords
- [ ] Handle all detection cases consistently

## Error Handling

- [ ] Raise `RateLimitError` with retry_after value
- [ ] Log rate limit errors with context
- [ ] Surface errors to user (no silent failures)
- [ ] Include status code and headers in error
- [ ] Distinguish rate limit from other errors

## Prohibited Patterns

- [ ] No immediate retry without backoff
- [ ] No ignoring `Retry-After` header
- [ ] No unbounded backoff (must have max)
- [ ] No silent failures on rate limit
- [ ] No hardcoded retry delays (use headers)

## Thresholds

- [ ] Circuit breaker: 3 failures to open
- [ ] Max backoff: 60 seconds
- [ ] Cooldown: 60 seconds
- [ ] Proactive throttle: <10% remaining
- [ ] Success threshold: 1 request to close circuit
