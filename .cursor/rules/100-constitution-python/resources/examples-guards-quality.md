# Examples: Guards and Quality Patterns

Code quality patterns and examples.

---

## Pure Functions Example

```python
def calculate_total(items: list[float]) -> float:
    """Calculate sum of items."""
    if not items:
        return 0.0
    return sum(items)
```

## Guard Clause Pattern

```python
def process_entity(entity_store: pl.DataFrame) -> pl.DataFrame:
    """Process entities with guard clauses."""
    # Guard 1: Empty check
    if entity_store.is_empty():
        return entity_store
    
    # Guard 2: Required columns
    if "entity_id" not in entity_store.columns:
        return entity_store
    
    # Single success path
    return entity_store.with_columns(
        pl.col("status").str.to_uppercase().alias("status")
    )
```

## Immutable Component Pattern

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class AuthConfig:
    """Pure data component - no methods."""
    api_key_ref: str
    base_url: str
    timeout_seconds: int = 30
```

## Forbidden Patterns

```python
# BAD: Mutable default
def add_item(item: str, items: list[str] = []):
    items.append(item)

# GOOD: Immutable default
def add_item(item: str, items: list[str] | None = None) -> list[str]:
    if items is None:
        items = []
    return items + [item]

# BAD: Magic number
timeout = time.time() + 300

# GOOD: Named constant
TIMEOUT_SECONDS = 300
timeout = time.time() + TIMEOUT_SECONDS
```
