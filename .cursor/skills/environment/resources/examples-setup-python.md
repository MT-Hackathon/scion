# Examples: Python Environment Setup (Rule Scripts)

Python environment setup for rule automation scripts.

---

## Purpose

Python is used for automation scripts in `.cursor/rules/*/scripts/`. These scripts handle:

- GitLab/GitHub API interactions
- Rule validation and scaffolding
- Conversation history analysis
- Code quality scanning

---

## uv Setup (Recommended)

### Install uv

**Windows (PowerShell)**:
```powershell
irm https://astral.sh/uv/install.ps1 | iex
```

**Linux/macOS**:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## Running Rule Scripts

### Using uv run (preferred)

```bash
uv run .cursor/skills/git-workflows/scripts/fetch_project.py
```

### Environment variables
Scripts auto-load from `.env` via `python-dotenv`:

```python
from dotenv import load_dotenv
import os

load_dotenv()
token = os.getenv("GITLAB_PERSONAL_ACCESS_TOKEN")
```

---

## PEP 723 Inline Dependencies

Scripts that need third-party packages declare them inline:

```python
#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = ["PyYAML>=6.0", "python-dotenv>=1.0"]
# ///

import yaml  # uv installs this automatically
```

When you run the script with `uv run`, dependencies are installed automatically to an isolated environment.

---

## Path Usage in Scripts

### Use pathlib for Cross-Platform Compatibility

```python
from pathlib import Path

# Project root
project_root = Path(__file__).resolve().parents[5]
# .cursor/skills/git-workflows/scripts/script.py -> project root

# Rule resources
rule_dir = Path(__file__).parent.parent
resources_dir = rule_dir / "resources"
```

### Anti-Pattern: Hardcoded Paths

```python
# BAD
data_path = "C:\\Users\\user\\projects\\procurement-web\\data"

# GOOD
data_path = Path(__file__).parent / "data"
```

---

## Troubleshooting

### uv not found
Ensure the `uv` binary is in your PATH. On Windows, this is typically `%USERPROFILE%\.cargo\bin`.

### Module not found (script without PEP 723 header)
Add inline dependencies to the script:

```python
#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = ["<missing-module>"]
# ///
```
