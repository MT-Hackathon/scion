# Examples: Shared Test Fixtures

TypeScript and Python fixture patterns for contract testing.

---

## Pattern

Identical test fixtures in both languages ensure the same data passes/fails validation on both sides.

---

## Project Implementation

### TypeScript Fixtures

```typescript
// tests/fixtures/api-source-configs.ts
export const validApiSourceConfig = {
  name: 'Test API',
  url: 'https://api.example.com',
  method: 'GET' as const,
  timeout: 30,
  authconfig_auth_type: 'none' as const
};

export const invalidApiSourceConfigs = {
  missingName: { ...validApiSourceConfig, name: '' },
  invalidUrl: { ...validApiSourceConfig, url: 'not-a-url' },
  invalidMethod: { ...validApiSourceConfig, method: 'INVALID' },
  timeoutTooHigh: { ...validApiSourceConfig, timeout: 500 }
};
```

### Python Fixtures

```python
# tests/fixtures/api_source_configs.py
VALID_API_SOURCE_CONFIG = {
    "name": "Test API",
    "url": "https://api.example.com",
    "method": "GET",
    "timeout": 30,
    "authconfig_auth_type": "none"
}

INVALID_API_SOURCE_CONFIGS = {
    "missing_name": {**VALID_API_SOURCE_CONFIG, "name": ""},
    "invalid_url": {**VALID_API_SOURCE_CONFIG, "url": "not-a-url"},
    "invalid_method": {**VALID_API_SOURCE_CONFIG, "method": "INVALID"},
    "timeout_too_high": {**VALID_API_SOURCE_CONFIG, "timeout": 500}
}
```

---

## Fixture Organization

| Location | Purpose |
|----------|---------|
| `tests/fixtures/` | Shared fixtures directory |
| `*-configs.ts` / `*_configs.py` | Config fixtures per entity type |
| Valid fixtures | Must pass both Zod and Pydantic |
| Invalid fixtures | Must fail both Zod and Pydantic |
