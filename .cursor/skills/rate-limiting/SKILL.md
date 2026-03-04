---
name: rate-limiting
description: "Governs rate limit detection, 429 handling, exponential backoff, and throttle-aware retry patterns for API integration. Use when consuming external APIs, implementing retry logic, or handling quota-exceeded and rate-limit-exceeded responses. DO NOT use for general concurrency patterns or HTTP client setup (see angular-http-reactive)."
---

<ANCHORSKILL-RATE-LIMITING>

# Rate Limit Principles Rule

## Table of Contents & Resources

### Blueprints
- [Exponential Backoff](blueprints/exponential-backoff.py): `with_exponential_backoff`
- [Circuit Breaker](blueprints/circuit-breaker.py): `CircuitBreaker` state machine
- [Rate-Limited Client](blueprints/rate-limited-client.py): `parse_rate_limit_headers`, `detect_rate_limit`, `RateLimitedApiClient`

### Resources
- [Core Concepts](#core-concepts)
- [Examples: Exponential Backoff](resources/examples-exponential-backoff.md)
- [Examples: Circuit Breaker](resources/examples-circuit-breaker.md)
- [Reference: Header Parsing](resources/reference-header-parsing.md)
- [Examples: Complete Client](resources/examples-complete-client.md)
- [Checklist: Rate Limit Implementation](resources/checklist-rate-limit-impl.md)
- [Cross-References](resources/cross-references.md)

## Core Concepts

### Exponential Backoff
1s initial, 2x multiplier, max 60s, reset on success

### Headers
Parse `Retry-After`; honor `X-RateLimit-Remaining` for proactive throttle; log all

### Circuit Breaker
Open after 3 consecutive 429s; half-open after 60s; reset after 1 success

### Detection
429 (primary), 503 (check Retry-After), 403 (quota exhaustion)

### Key Headers
`X-RateLimit-Limit` (total), `X-RateLimit-Remaining` (left), `X-RateLimit-Reset` (timestamp), `Retry-After` (delay)

### Prohibited
Immediate retry without backoff, ignoring Retry-After, no max cap, silent failures

### Thresholds
Circuit 3 failures, max backoff 60s, cooldown 60s, proactive <10% remaining

</ANCHORSKILL-RATE-LIMITING>
