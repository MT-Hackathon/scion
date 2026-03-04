# Reference: Python Imports

Import organization and JSON parsing patterns.

---

## Import Grouping and Ordering

```python
# GOOD: Properly grouped and ordered
# Standard library
import json
import os
from typing import Optional

# Third-party
import httpx
import polars as pl
from pydantic import BaseModel

# First-party
from src.backend.api.routes import router
from src.backend.core.config import settings
from src.backend.systems.validation import validate_entity_store
```

## Absolute Imports

```python
# BAD: Relative imports with hops
from ..config import settings
from ...core.utils import helper

# GOOD: Absolute imports
from src.backend.core.config import settings
from src.backend.core.utils import helper
```

## Specific Imports (No Wildcards)

```python
# BAD: Wildcard import
from src.backend.systems import *

# GOOD: Specific imports
from src.backend.systems import (
    validation_system,
    transformation_system,
    enrichment_system
)
```

## Top-Level Imports

```python
# BAD: In-function import (unless optional dependency)
def process_data():
    import pandas as pd
    return pd.DataFrame()

# GOOD: Top-level import
import polars as pl

def process_data():
    return pl.DataFrame()

# ACCEPTABLE: Optional dependency
def export_to_excel():
    try:
        import openpyxl
    except ImportError:
        raise ImportError("openpyxl required for Excel export")
```

## JSON Parsing Fallback

```python
import ast
import json

def parse_json_string(data: str) -> dict:
    """Parse JSON with fallback for trusted strings."""
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        # Fallback for trusted strings only
        try:
            return ast.literal_eval(data)
        except (ValueError, SyntaxError):
            raise ValueError(f"Invalid JSON/literal: {data}")

# NEVER: Use eval
def bad_parse(data: str):
    return eval(data)  # SECURITY RISK
```
