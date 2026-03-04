# Reference: Shared Fixtures

Fixture organization for frontend/backend test alignment.

---

## Pattern

Same fixtures in both TypeScript and Python ensure the same data passes/fails on both sides.

See also: [data-contracts examples-shared-fixtures](../../data-contracts/resources/examples-shared-fixtures.md)

---

## Project Implementation

### Python Fixtures

```python
# tests/fixtures/pipeline_configs.py
"""Shared fixtures valid against both Pydantic and Zod."""

VALID_PIPELINE_CONFIG = {
    "name": "Test Pipeline",
    "nodes": [
        {
            "id": "node-1",
            "type": "apiSource",
            "position": {"x": 100, "y": 100},
            "data": {
                "name": "My API",
                "url": "https://api.example.com",
                "method": "GET",
                "timeout": 30
            }
        }
    ],
    "edges": []
}

INVALID_PIPELINE_CONFIGS = {
    "empty_name": {**VALID_PIPELINE_CONFIG, "name": ""},
    "missing_nodes": {**VALID_PIPELINE_CONFIG, "nodes": []},
    "invalid_url": {
        **VALID_PIPELINE_CONFIG,
        "nodes": [{
            **VALID_PIPELINE_CONFIG["nodes"][0],
            "data": {
                **VALID_PIPELINE_CONFIG["nodes"][0]["data"],
                "url": "not-a-url"
            }
        }]
    }
}
```

### TypeScript Fixtures

```typescript
// tests/fixtures/pipeline-configs.ts
export const validPipelineConfig = {
  name: 'Test Pipeline',
  nodes: [
    {
      id: 'node-1',
      type: 'apiSource' as const,
      position: { x: 100, y: 100 },
      data: {
        name: 'My API',
        url: 'https://api.example.com',
        method: 'GET' as const,
        timeout: 30
      }
    }
  ],
  edges: []
};

export const invalidPipelineConfigs = {
  emptyName: { ...validPipelineConfig, name: '' },
  missingNodes: { ...validPipelineConfig, nodes: [] },
  invalidUrl: {
    ...validPipelineConfig,
    nodes: [{
      ...validPipelineConfig.nodes[0],
      data: {
        ...validPipelineConfig.nodes[0].data,
        url: 'not-a-url'
      }
    }]
  }
};
```

---

## Fixture Organization

| Location | Purpose |
|----------|---------|
| `tests/fixtures/` | Shared fixtures directory |
| `tests/unit/` | Unit tests |
| `tests/integration/` | Integration tests |
| `tests/e2e/` | End-to-end tests |

---

## Anti-Patterns

```python
# ❌ BAD: Divergent fixtures
# Backend fixture
backend_config = {"name": "Test", "url": "http://example.com"}
# Frontend fixture (different!)
frontend_config = {"name": "Test", "endpoint": "http://example.com"}

# ✅ GOOD: Shared fixtures
# tests/fixtures/ used by both frontend and backend
```
