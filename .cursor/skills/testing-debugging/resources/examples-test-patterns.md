# Patterns: Constitution Testing & Debugging

Testing and debugging workflow patterns.

---

## Unit Test Pattern

```python
def test_calculate_total_empty():
    """Test with empty input."""
    result = calculate_total([])
    assert result == 0.0

def test_calculate_total_normal():
    """Test with normal input."""
    result = calculate_total([1.0, 2.0, 3.0])
    assert result == 6.0

def test_calculate_total_none():
    """Test with None input."""
    result = calculate_total(None)
    assert result == 0.0
```

## Backend Debug Workflow

```
1. Bug reported: "API returns 500 on /api/pipeline/execute"
2. Add logging: log.debug(f"Executing pipeline {pipeline_id}")
3. Write unit test: test_execute_pipeline_with_invalid_config()
4. Run test, capture stack trace
5. Fix code: add guard clause for missing config
6. Re-test: verify fix
```

## UI Debug Workflow

```
1. Bug reported: "Save button doesn't work"
2. Navigate to page with browser tools
3. Snapshot page state
4. Check console for errors
5. Check network tab for failed requests
6. Click button, observe interaction
7. Read component code
8. Fix code
9. Screenshot BEFORE vs AFTER (required)
10. Re-test
```

## Test Failure Diagnostic Order

```
Test fails: test_api_authentication()
↓
1. Check test validity: Is assertion correct?
   → Yes, test expects 200 status
↓
2. Check environment: conda activated?
   → Run: conda info --envs
↓
3. Check configuration: API keys present?
   → Run: echo $API_KEY (without reading .env)
↓
4. Check test infrastructure: pytest working?
   → Run: pytest --version
↓
5. NOW investigate code bug
```
