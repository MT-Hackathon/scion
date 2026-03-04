# Reference: DataFrame Storage

Polars DataFrame storage patterns for ECS entity stores.

---

## Basic System Signature

```python
import polars as pl

def validate_entities_system(entity_store: pl.DataFrame) -> pl.DataFrame:
    """System with proper signature."""
    if entity_store.is_empty():
        return entity_store
    
    return entity_store.with_columns(
        pl.col("status").str.to_uppercase().alias("status")
    )
```

## Guard Clauses Pattern

```python
def process_system(entity_store: pl.DataFrame) -> pl.DataFrame:
    """System with guard clauses."""
    # Guard 1: Empty check
    if entity_store.is_empty():
        return entity_store
    
    # Guard 2: Required columns
    required_cols = {"entity_id", "status", "data"}
    if not required_cols.issubset(entity_store.columns):
        return entity_store
    
    # Single success path
    return entity_store.filter(pl.col("status") == "active")
```

## Copy-on-Write Pattern

```python
def modify_system(entity_store: pl.DataFrame) -> pl.DataFrame:
    """Copy-on-write before modification."""
    if entity_store.is_empty():
        return entity_store
    
    # Polars is copy-on-write by default
    # with_columns() returns new DataFrame
    return entity_store.with_columns(
        pl.col("counter").add(1).alias("counter")
    )
```

## Vectorization Pattern

```python
# BAD: Row-wise loop
def bad_process(entity_store: pl.DataFrame) -> pl.DataFrame:
    for row in entity_store.iter_rows(named=True):
        pass

# GOOD: Vectorized operation
def good_process(entity_store: pl.DataFrame) -> pl.DataFrame:
    if entity_store.is_empty():
        return entity_store
    
    return entity_store.with_columns([
        (pl.col("value") * 2).alias("doubled"),
        pl.col("status").str.to_uppercase().alias("status")
    ])
```

## Component Field Filtering

```python
def add_auth_config_system(
    entity_store: pl.DataFrame,
    auth_config: dict[str, Any]
) -> pl.DataFrame:
    """Add component fields with None filtering."""
    if entity_store.is_empty():
        return entity_store
    
    # Filter None values before adding
    filtered_config = {
        f"authconfig_{k}": v 
        for k, v in auth_config.items() 
        if v is not None
    }
    
    # Add columns with defaults for missing values
    return entity_store.with_columns([
        pl.lit(v).alias(k) for k, v in filtered_config.items()
    ])
```

## Storage Decision Pattern

| Criteria | Polars DataFrame | esper (sparse) |
|----------|------------------|----------------|
| Entity count | >100 | <100 |
| Density | >70% | <30% |
| Operations | Bulk/batch | Event-driven |
| Use case | Analytics | Lifecycle |
