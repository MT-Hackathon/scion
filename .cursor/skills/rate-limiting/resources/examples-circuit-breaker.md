# Examples: Circuit Breaker

Circuit breaker state machine for rate limit failures.

**Blueprint:** `../blueprints/circuit-breaker.py` — `CircuitBreaker` class.

---

## State Transitions

| From | To | Trigger |
|------|----|---------|
| CLOSED | OPEN | 3 consecutive failures |
| OPEN | HALF_OPEN | 60s cooldown elapsed |
| HALF_OPEN | CLOSED | 1 successful request |
| HALF_OPEN | OPEN | Any failure |

---

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| failure_threshold | 3 | Failures to open circuit |
| cooldown_seconds | 60 | Time before half-open |
| success_threshold | 1 | Successes to close circuit |
