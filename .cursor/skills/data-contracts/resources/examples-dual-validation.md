# Examples: Dual Validation

Parallel validation patterns for frontend (Zod) and backend (Pydantic).

---

## Pattern

Both layers validate the same data contract with equivalent rules. Frontend validates at form submit and before API calls; backend validates on pipeline execution.

---

## Project Implementation

### Frontend (Zod)

```typescript
import { z } from 'zod';

const apiSourceConfigSchema = z.object({
  name: z.string().min(1, "Name is required"),
  url: z.string().url("Must be a valid URL"),
  method: z.enum(['GET', 'POST', 'PUT', 'DELETE']),
  timeout: z.number().int().min(1).max(300),
  authconfig_auth_type: z.enum(['none', 'api_key', 'oauth2']).default('none'),
  authconfig_api_key_ref: z.string().optional()
});

// Validate at form submit
function submitForm(data: unknown) {
  const result = apiSourceConfigSchema.safeParse(data);
  
  if (!result.success) {
    // Show inline errors
    setErrors(result.error.flatten().fieldErrors);
    return;
  }
  
  // Send to backend
  await saveConfig(result.data);
}

// Validate before API call
async function saveConfig(config: ApiSourceConfig) {
  // Re-validate before sending
  const result = apiSourceConfigSchema.safeParse(config);
  if (!result.success) {
    throw new Error('Invalid config');
  }
  
  await fetch(`${API_URL}/api/sources`, {
    method: 'POST',
    body: JSON.stringify(result.data)
  });
}
```

### Backend (Pydantic)

```python
from pydantic import BaseModel, Field, HttpUrl
from typing import Literal

class ApiSourceConfig(BaseModel):
    """API Source configuration - matches frontend schema."""
    name: str = Field(min_length=1)
    url: HttpUrl
    method: Literal['GET', 'POST', 'PUT', 'DELETE']
    timeout: int = Field(ge=1, le=300)
    authconfig_auth_type: Literal['none', 'api_key', 'oauth2'] = 'none'
    authconfig_api_key_ref: str | None = None

# Validate on pipeline execution
def execute_pipeline(config: dict) -> dict:
    """Execute pipeline with validated config."""
    try:
        validated = ApiSourceConfig.model_validate(config)
    except ValidationError as err:
        return {
            "status": "error",
            "error": {"code": "INVALID_CONFIG", "message": str(err)}
        }
    
    # Execute with validated config
    result = run_pipeline(validated)
    return {"status": "success", "data": result}
```

---

## Prohibited Patterns

```typescript
// ❌ BAD: Schema divergence
// Frontend: url is optional
const frontendSchema = z.object({
  url: z.string().url().optional()
});

// Backend: url is required
class BackendModel(BaseModel):
  url: HttpUrl  # Required

// ✅ GOOD: Both sides match
// Frontend and backend both require URL

// ❌ BAD: Different validation rules
// Frontend: timeout 1-300
const frontend = z.number().min(1).max(300);

// Backend: timeout 1-60
timeout: int = Field(ge=1, le=60)

// ✅ GOOD: Same validation on both sides

// ❌ BAD: Runtime modification without re-validation
const config = validated;
config.url = newUrl; // Not re-validated!
await saveConfig(config);

// ✅ GOOD: Re-validate after modification
const modified = { ...validated, url: newUrl };
const result = schema.safeParse(modified);
if (result.success) {
  await saveConfig(result.data);
}
```
