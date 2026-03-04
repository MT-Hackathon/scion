# Patterns: ECS Architecture

ECS implementation patterns and examples.

---

## Component Pattern

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class PositionComponent:
    """Pure data component - no methods."""
    x: float
    y: float
    z: float

@dataclass(frozen=True)
class VelocityComponent:
    """Pure data component - no methods."""
    dx: float
    dy: float
    dz: float
```

## System Pattern

```python
def movement_system(
    entity_store: pl.DataFrame,
    delta_time: float
) -> pl.DataFrame:
    """Pure function: DataFrame → DataFrame."""
    # Guard clauses
    if entity_store.is_empty():
        return entity_store
    
    required_cols = {"position_x", "position_y", "velocity_dx", "velocity_dy"}
    if not required_cols.issubset(entity_store.columns):
        return entity_store
    
    # Pure transformation
    return entity_store.with_columns([
        (pl.col("position_x") + pl.col("velocity_dx") * delta_time).alias("position_x"),
        (pl.col("position_y") + pl.col("velocity_dy") * delta_time).alias("position_y")
    ])
```

## Multi-Store System Pattern

```python
def cached_api_system(
    entity_store: pl.DataFrame,
    cache_store: pl.DataFrame,
    api_client: Optional[ApiClient] = None
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """System with cache DataFrame."""
    # Guard clauses
    if entity_store.is_empty():
        return entity_store, cache_store
    
    # Check cache first
    cached = entity_store.join(
        cache_store,
        on="entity_id",
        how="left"
    )
    
    # Process only uncached entities
    needs_fetch = cached.filter(pl.col("cached_response").is_null())
    
    if needs_fetch.is_empty():
        return entity_store, cache_store
    
    # Fetch and update cache
    # ... fetch logic ...
    
    return updated_entity_store, updated_cache_store
```

## System Composition Pattern

```python
def compose_system_pipeline(*systems):
    """Compose multiple systems into a pipeline."""
    def pipeline(entity_store: pl.DataFrame, *args, **kwargs) -> pl.DataFrame:
        result = entity_store
        for system in systems:
            result = system(result, *args, **kwargs)
        return result
    return pipeline

# Usage
pipeline = compose_system_pipeline(
    validation_system,
    transformation_system,
    enrichment_system
)
result = pipeline(entity_store, delta_time=1.0)
```

## Resource Pattern

```python
from dataclasses import dataclass

@dataclass
class ApiClientResource:
    """Stateful resource - stores IDs, not instances."""
    base_url: str
    timeout_seconds: int
    
    def create_client(self):
        """Factory method for client instances."""
        return httpx.Client(base_url=self.base_url, timeout=self.timeout_seconds)
```

## Response Storage Pattern

```python
def api_fetch_system(
    entity_store: pl.DataFrame,
    api_client: Optional[httpx.Client] = None
) -> pl.DataFrame:
    """Store API responses as JSON strings."""
    if entity_store.is_empty():
        return entity_store
    
    # Fetch API data
    responses = []
    for entity_id in entity_store["entity_id"]:
        response = api_client.get(f"/data/{entity_id}")
        responses.append(response.json())
    
    # Store as JSON string column
    return entity_store.with_columns(
        pl.Series("api_response", [json.dumps(r) for r in responses])
    )
```

## Storage Selection Decision Tree

**Choose Polars DataFrame storage when:**
- Entity count > 100
- Component density > 70% (most entities have most components)
- Bulk operations and batch processing
- Analytics and aggregation queries
- Vectorization opportunities

**Choose esper (sparse storage) when:**
- Entity count < 100
- Component density < 30% (sparse entities)
- Event-driven individual operations
- Lifecycle management needs
- Simple presence queries

**Choose hybrid approach when:**
- Mixed density (some dense, some sparse)
- Need both orchestration and data processing
- Event-driven with bulk operations

## FastAPI Integration Pattern

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import polars as pl

app = FastAPI()

# Pydantic request model
class EntityRequest(BaseModel):
    entity_type: str
    position_x: float
    position_y: float

# ECS Component (pure dataclass)
@dataclass(frozen=True)
class PositionComponent:
    x: float
    y: float

# System (pure function)
def process_entities(entity_store: pl.DataFrame) -> pl.DataFrame:
    if entity_store.is_empty():
        return entity_store
    # Vectorized processing
    return entity_store.with_columns(
        pl.col("position_x").alias("processed_x")
    )

# FastAPI endpoint (thin orchestration)
@app.post("/entities/")
async def create_entity(request: EntityRequest):
    # Validate with Pydantic
    if not request.entity_type:
        raise HTTPException(status_code=400, detail="entity_type required")
    
    # Convert to DataFrame
    entity_df = pl.DataFrame([{
        'entity_id': generate_id(),
        'entity_type': request.entity_type,
        'position_x': request.position_x,
        'position_y': request.position_y
    }])
    
    # Process through system
    result_df = process_entities(entity_df)
    
    # Return response
    return {"entity_id": result_df["entity_id"][0], "status": "created"}
```

## Implementation Principle Summary

**Core ECS Architecture in Universal-API:**
- Entities = IDs only (no methods/behavior)
- Components = pure dataclasses in `src/backend/core/ecs_architecture.py`
- Systems = pure functions with `*_system` suffix (DataFrame → DataFrame)
- Component fields map to column prefixes: `endpointconfig_*`, `authconfig_*`, etc.
- Guard clauses precede all logic
- Vectorized operations only (no Python loops)
- Lazy evaluation (`.lazy()`) for chained systems
- Never use esper - project is Polars-only
