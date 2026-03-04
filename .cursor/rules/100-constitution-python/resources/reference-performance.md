# Reference: Performance Patterns

Performance optimization patterns for backend.

---

## Vectorized Operations

```python
import polars as pl

# BAD: Row-wise iteration
def slow_process(entity_store: pl.DataFrame) -> pl.DataFrame:
    results = []
    for row in entity_store.iter_rows(named=True):
        results.append(row["value"] * 2)
    return entity_store.with_columns(pl.Series("doubled", results))

# GOOD: Vectorized operation
def fast_process(entity_store: pl.DataFrame) -> pl.DataFrame:
    return entity_store.with_columns(
        (pl.col("value") * 2).alias("doubled")
    )
```

## Keep Data Columnar

```python
# BAD: Convert to Python objects
def slow_aggregation(entity_store: pl.DataFrame) -> float:
    values = entity_store["value"].to_list()  # Conversion!
    return sum(values) / len(values)

# GOOD: Stay columnar
def fast_aggregation(entity_store: pl.DataFrame) -> float:
    return entity_store["value"].mean()
```

## DataFrame Cache Pattern

```python
# BAD: Module-level cache
_CACHE = {}

def bad_cached_system(entity_store: pl.DataFrame) -> pl.DataFrame:
    if entity_id not in _CACHE:
        _CACHE[entity_id] = fetch_data(entity_id)
    return entity_store

# GOOD: DataFrame cache
def good_cached_system(
    entity_store: pl.DataFrame,
    cache_store: pl.DataFrame
) -> tuple[pl.DataFrame, pl.DataFrame]:
    return updated_entity_store, updated_cache_store
```

## Lazy Evaluation & Predicate Pushdown

```python
# BAD: Eager loading
df = pl.read_csv('large_file.csv')
filtered = df.filter(pl.col('amount') > 150)

# GOOD: Lazy with predicate pushdown
df_lazy = pl.scan_csv('large_file.csv')
optimized = (df_lazy
    .filter(pl.col('amount') > 150)
    .group_by('category')
    .agg(pl.col('amount').sum())
)
result = optimized.collect()
```

## Memory Optimization with Dtypes

```python
# GOOD: Optimize dtypes
schema = {
    'id': pl.Int32,              # Int32 vs Int64 (50% memory)
    'status': pl.Categorical,    # For repeated strings
    'score': pl.Float32,         # Float32 vs Float64 (50% memory)
    'active': pl.Boolean         # 1 byte vs 8 bytes
}
df = pl.read_csv('data.csv', dtypes=schema)
```

## Streaming for Large Datasets

```python
# BAD: Load entire dataset into memory
df = pl.read_csv('huge_file.csv')

# GOOD: Stream processing
df_lazy = pl.scan_csv('huge_file.csv')
result = df_lazy.filter(pl.col('status') == 'active').collect(streaming=True)
```

## When to Apply Optimization Strategies

| Strategy | Use When | Expected Gain |
|----------|----------|---------------|
| Vectorization | >1k rows, loops present | 10-100x speedup |
| Lazy evaluation | Chained operations | 2-10x speedup |
| Column projection | >10 columns, few needed | 50-90% memory |
| Dtype optimization | Large datasets | 30-70% memory |
| Streaming | Data > RAM | Enables processing |
