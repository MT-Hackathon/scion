# Examples: Contract Synchronization

Schema update workflow and testing alignment patterns.

---

## Pattern

`data-contracts-context.md` is the single source of truth. All schema changes start there, then propagate to Zod, Pydantic, and tests.

---

## Project Implementation

### Source of Truth Format

```markdown
# data-contracts-context.md (Source of Truth)

## ApiSourceConfig

| Field | Type | Frontend (Zod) | Backend (Pydantic) | Required | Validation |
|-------|------|----------------|-------------------|----------|------------|
| name | string | z.string().min(1) | str, Field(min_length=1) | Yes | Non-empty |
| url | URL string | z.string().url() | HttpUrl | Yes | Valid URL |
| method | enum | z.enum(['GET',...]) | Literal['GET',...] | Yes | HTTP method |
| timeout | integer | z.number().int().min(1).max(300) | int, Field(ge=1, le=300) | Yes | 1-300 |
```

### Testing Contract Alignment

**Frontend test:**

```typescript
import { describe, it, expect } from 'vitest';

describe('ApiSourceConfig validation', () => {
  it('accepts valid config', () => {
    const valid = {
      name: 'My API',
      url: 'https://api.example.com',
      method: 'GET',
      timeout: 30
    };
    
    expect(apiSourceConfigSchema.safeParse(valid).success).toBe(true);
  });
  
  it('rejects invalid URL', () => {
    const invalid = {
      name: 'My API',
      url: 'not-a-url',
      method: 'GET',
      timeout: 30
    };
    
    const result = apiSourceConfigSchema.safeParse(invalid);
    expect(result.success).toBe(false);
  });
});
```

**Backend test:**

```python
import pytest
from pydantic import ValidationError

def test_api_source_config_valid():
    """Test valid config passes validation."""
    valid = {
        "name": "My API",
        "url": "https://api.example.com",
        "method": "GET",
        "timeout": 30
    }
    
    config = ApiSourceConfig.model_validate(valid)
    assert config.name == "My API"

def test_api_source_config_invalid_url():
    """Test invalid URL fails validation."""
    invalid = {
        "name": "My API",
        "url": "not-a-url",
        "method": "GET",
        "timeout": 30
    }
    
    with pytest.raises(ValidationError):
        ApiSourceConfig.model_validate(invalid)
```

---

## Sync Workflow

1. Update `data-contracts-context.md` (source of truth)
2. Update Zod schema in frontend
3. Update Pydantic model in backend
4. Run tests on both sides with same fixtures
5. Update API types if needed
