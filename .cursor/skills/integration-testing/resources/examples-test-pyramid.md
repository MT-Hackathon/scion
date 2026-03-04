# Examples: Test Pyramid

Unit, Integration, and E2E test examples following the test pyramid.

---

## Pattern

```
         /\
        /E2E\ (~10%)
       /------\
      /  Integ \ (~20%)
     /----------\
    /    Unit    \ (~70%)
   /--------------\
```

---

## Project Implementation

### Unit Test Example (70%)

```python
# tests/unit/test_validation.py
import pytest
from pydantic import ValidationError
from models import ApiSourceConfig

def test_api_source_valid():
    """Unit test for config validation."""
    config = ApiSourceConfig(
        name="Test API",
        url="https://api.example.com",
        method="GET",
        timeout=30
    )
    assert config.name == "Test API"

def test_api_source_invalid_url():
    """Unit test for invalid URL."""
    with pytest.raises(ValidationError):
        ApiSourceConfig(
            name="Test API",
            url="not-a-url",
            method="GET",
            timeout=30
        )
```

### Integration Test Example (20%)

```python
# tests/integration/test_api_handlers.py
import pytest
from fastapi.testclient import TestClient
from backend.web_api import app

client = TestClient(app)

def test_create_pipeline_success():
    """Integration test for pipeline creation handler."""
    payload = {
        "name": "Test Pipeline",
        "nodes": [
            {"id": "1", "type": "apiSource", "data": {...}}
        ],
        "edges": []
    }
    
    response = client.post("/api/pipelines", json=payload)
    
    assert response.status_code == 200
    result = response.json()
    assert result["success"] is True
    assert "id" in result["data"]

def test_create_pipeline_invalid_payload():
    """Integration test for invalid payload."""
    payload = {
        "name": "",  # Invalid: empty name
        "nodes": [],
        "edges": []
    }
    
    response = client.post("/api/pipelines", json=payload)
    
    assert response.status_code == 400
    result = response.json()
    assert result["success"] is False
    assert result["error"]["code"] == "INVALID_CONFIG"

def test_create_pipeline_malformed_json():
    """Integration test for malformed JSON."""
    response = client.post(
        "/api/pipelines",
        data="not json",
        headers={"Content-Type": "application/json"}
    )
    
    assert response.status_code == 422
```

### E2E Test Example (10%)

```typescript
// tests/e2e/pipeline-creation.test.ts
import { test, expect } from '@playwright/test';

test('create and save pipeline', async ({ page }) => {
  // Navigate to app
  await page.goto('http://localhost:4173');
  
  // Create pipeline
  await page.click('[data-testid="new-pipeline"]');
  await page.fill('[data-testid="pipeline-name"]', 'Test Pipeline');
  
  // Add API source node
  await page.click('[data-testid="add-api-source"]');
  await page.fill('[data-testid="source-name"]', 'My API');
  await page.fill('[data-testid="source-url"]', 'https://api.example.com');
  
  // Save pipeline
  await page.click('[data-testid="save-pipeline"]');
  
  // Verify success
  await expect(page.locator('[data-testid="success-toast"]')).toBeVisible();
  
  // Verify backend received request
  const response = await page.waitForResponse(
    resp => resp.url().includes('/api/pipelines') && resp.status() === 200
  );
  const body = await response.json();
  expect(body.success).toBe(true);
});
```

---

## Anti-Patterns

```python
# ❌ BAD: Integration test without unit coverage
def test_pipeline_creation():
    """Integration test with no unit tests for validation logic."""
    response = client.post("/api/pipelines", json=payload)
    assert response.status_code == 200

# ✅ GOOD: Unit tests first, then integration
# tests/unit/test_pipeline_validation.py has unit tests
# tests/integration/test_pipeline_handlers.py has integration tests

# ❌ BAD: Flaky timing
def test_async_operation():
    trigger_operation()
    time.sleep(0.5)  # Hope it finishes in 500ms!
    assert operation_complete()

# ✅ GOOD: Explicit waiting
def test_async_operation():
    trigger_operation()
    wait_for_condition(lambda: operation_complete(), timeout=5)
```
