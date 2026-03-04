# Examples: Python Test Patterns (Rule Scripts)

Testing patterns for Python rule scripts using pytest.

---

## Basic Test Structure

```python
import pytest
from pathlib import Path


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

---

## Test Fixtures

```python
import pytest


@pytest.fixture
def sample_config():
    """Provide sample configuration for tests."""
    return {
        "api_url": "https://api.example.com",
        "timeout": 30,
    }


@pytest.fixture
def temp_file(tmp_path):
    """Create temporary file for testing."""
    file_path = tmp_path / "test.txt"
    file_path.write_text("test content")
    return file_path


def test_with_config(sample_config):
    """Test using fixture."""
    assert sample_config["timeout"] == 30
```

---

## Script Debug Workflow

```
1. Bug reported: "GitLab script returns empty results"
2. Add logging: logging.debug(f"Fetching from {url}")
3. Write unit test: test_fetch_projects_with_token()
4. Run test, capture output
5. Fix code: handle pagination
6. Re-test: verify fix
```

---

## Test Failure Diagnostic Order

```
Test fails: test_gitlab_api.py
↓
1. Check test validity: Is assertion correct?
   → Yes, expects list of projects
↓
2. Check environment: uv installed?
   → Run: uv --version
↓
3. Check configuration: API keys present?
   → Verify .env has GITLAB_PERSONAL_ACCESS_TOKEN
↓
4. Check test infrastructure: pytest working?
   → Run: uv run pytest --version
↓
5. NOW investigate code bug
```

---

## Running Python Tests

```bash
# Run all tests in a directory
uv run pytest .cursor/skills/git-workflows/scripts/

# Run specific test file
uv run pytest test_gitlab_api.py

# Run with verbose output
uv run pytest -v test_script.py

# Run single test function
uv run pytest test_script.py::test_specific_function
```

---

## Mocking External Services

```python
from unittest.mock import patch, MagicMock


@patch('requests.get')
def test_fetch_data(mock_get):
    """Test API call with mocked response."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": "test"}
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    result = fetch_data("https://api.example.com")
    
    assert result == {"data": "test"}
    mock_get.assert_called_once()
```

---

## Environment Variable Testing

```python
import os
from unittest.mock import patch


@patch.dict(os.environ, {"GITLAB_PERSONAL_ACCESS_TOKEN": "test-token"})
def test_with_token():
    """Test with mocked environment variable."""
    token = os.getenv("GITLAB_PERSONAL_ACCESS_TOKEN")
    assert token == "test-token"
```
