# Reference: Forbidden Patterns

Patterns that violate NASA-grade code quality standards.

---

## Forbidden Patterns

| Pattern | Why Forbidden | Fix |
|---------|---------------|-----|
| Bare except / catch-all | Swallows errors, hides bugs | Catch specific exceptions |
| Global mutable state | Hidden dependencies, race conditions | Pass state explicitly |
| Magic numbers | Unclear intent, hard to change | Use named constants |
| Mutable defaults | Shared state between calls | Use None and create inside |
| Unbounded retry | Can hang indefinitely | Set max retries + backoff |
| Nested error handling >3 | Unreadable | Refactor to smaller functions |
| Type comments | Outdated style | Use type annotations |

---

## Examples

### Magic Numbers

```python
# BAD
if retry_count > 3:
    timeout = 30

# GOOD
MAX_RETRIES = 3
DEFAULT_TIMEOUT_SECONDS = 30

if retry_count > MAX_RETRIES:
    timeout = DEFAULT_TIMEOUT_SECONDS
```

### Mutable Defaults

```python
# BAD
def process(items: list = []):
    items.append("new")  # Shared across calls!
    return items

# GOOD
def process(items: list | None = None):
    if items is None:
        items = []
    items.append("new")
    return items
```

### Unbounded Retry

```python
# BAD
while True:
    try:
        result = fetch_data()
        break
    except ConnectionError:
        time.sleep(1)  # Forever loop risk

# GOOD
MAX_RETRIES = 5
for attempt in range(MAX_RETRIES):
    try:
        result = fetch_data()
        break
    except ConnectionError:
        if attempt == MAX_RETRIES - 1:
            raise
        time.sleep(2 ** attempt)  # Exponential backoff
```
