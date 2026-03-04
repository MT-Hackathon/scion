# Reference: Approved Packages

Approved package selections for backend Python development.

---

## Pattern

Backend packages are selected for type safety, performance, and async support.

### API Framework
| Package | Purpose | Notes |
|---------|---------|-------|
| `fastapi` | HTTP API routing | Async routes, automatic OpenAPI docs |
| `uvicorn` | ASGI server | Production-ready, async |
| `pydantic` | Validation | Dataclasses without methods |

### Data Processing
| Package | Purpose | Notes |
|---------|---------|-------|
| `polars` | DataFrames | Vectorized, copy-on-write, pure functions |
| `snowpark pandas` | Snowflake integration | Optional, for Snowflake workloads |

### Cloud & Infrastructure
| Package | Purpose | Notes |
|---------|---------|-------|
| `boto3` | AWS SDK | With type stubs for type safety |

---

## Project Implementation

### FastAPI Route Example

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

class PipelineRequest(BaseModel):
    name: str
    nodes: list[dict]

@router.post("/api/pipelines")
async def create_pipeline(request: PipelineRequest):
    """Create a new pipeline."""
    return {"status": "success", "data": {"id": "123"}}
```

### Polars DataFrame Example

```python
import polars as pl

def process_entities(entity_store: pl.DataFrame) -> pl.DataFrame:
    """Process entities using pure Polars operations."""
    if entity_store.is_empty():
        return entity_store
    
    return entity_store.with_columns(
        pl.col("status").str.to_uppercase().alias("status")
    )
```

---

## Prohibited Packages

```python
# ❌ BAD: Using Flask
from flask import Flask
app = Flask(__name__)

# ✅ GOOD: Using FastAPI
from fastapi import FastAPI
app = FastAPI()

# ❌ BAD: Using Pandas
import pandas as pd
df = pd.DataFrame(data)

# ✅ GOOD: Using Polars
import polars as pl
df = pl.DataFrame(data)
```

---

## Package Review Checklist

Before adding new backend dependencies:

- [ ] Check if existing approved packages can solve the need
- [ ] Verify package is actively maintained (commits within 6 months)
- [ ] Check license compatibility (MIT, Apache 2.0, BSD preferred)
- [ ] Verify package has type stubs available
- [ ] Confirm package doesn't duplicate existing functionality
- [ ] Using FastAPI for API routes (not Flask)
- [ ] Using Polars for DataFrame operations (not Pandas)
- [ ] Using Pydantic for validation (frozen dataclasses, no methods)
- [ ] Using boto3 with type stubs for AWS operations
- [ ] No ORMs or class-based data models
