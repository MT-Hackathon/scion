# Examples: HTTP Flow Testing

Envelope validation, error codes, and timeout testing patterns.

---

## Pattern

Test the HTTP layer contract: envelope structure, error codes, and timeout handling.

---

## Project Implementation

```python
# tests/integration/test_http_flows.py
import pytest
from fastapi.testclient import TestClient
from backend.web_api import app

client = TestClient(app)

def test_request_response_envelope():
    """Test standard envelope format."""
    response = client.get("/api/pipelines")
    result = response.json()
    
    # Verify envelope structure
    assert "success" in result
    assert result["success"] in [True, False]
    
    # Guard: validate error envelope fields when request fails
    if not result["success"]:
        assert "error" in result
        assert "code" in result["error"]
        assert "message" in result["error"]
        return
    assert "data" in result

def test_error_codes():
    """Test error code consistency."""
    # Invalid config
    response = client.post("/api/pipelines", json={"name": ""})
    result = response.json()
    assert result["error"]["code"] == "INVALID_CONFIG"
    
    # Not found
    response = client.get("/api/pipelines/nonexistent")
    result = response.json()
    assert result["error"]["code"] == "RESOURCE_NOT_FOUND"
    
    # Timeout
    response = client.post("/api/pipelines/execute", json={"id": "timeout-test"})
    result = response.json()
    assert result["error"]["code"] == "TIMEOUT"

def test_timeout_handling():
    """Test request timeout."""
    import time
    
    # Mock slow operation
    def slow_operation():
        time.sleep(35)  # Exceeds 30s timeout
    
    response = client.post("/api/slow-operation")
    
    assert response.status_code == 504
    result = response.json()
    assert result["error"]["code"] == "TIMEOUT"
```

---

## Envelope Structure

### Success Response

```json
{
  "success": true,
  "data": { ... }
}
```

### Error Response

```json
{
  "success": false,
  "error": {
    "code": "INVALID_CONFIG",
    "message": "Name is required"
  }
}
```

---

## Error Codes to Test

| Code | HTTP Status | Test Case |
|------|-------------|-----------|
| `INVALID_CONFIG` | 400 | Empty/invalid payload |
| `RESOURCE_NOT_FOUND` | 404 | Nonexistent resource |
| `TIMEOUT` | 504 | Long-running operation |
| `UNAUTHORIZED` | 401 | Missing/invalid auth |
| `VALIDATION_ERROR` | 400 | Schema validation failure |
