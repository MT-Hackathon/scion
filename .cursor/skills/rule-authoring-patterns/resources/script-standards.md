# Script Standardization Patterns

Canonical reference for script architecture, output, and documentation within the procurement ecosystem.

## 1. Design Philosophy
Scripts are **agent tools**. They save tokens by performing deterministic work that doesn't require AI reasoning. They must be **portable** and **project-agnostic**—no hardcoded project names, repo paths, or URLs.

## 2. Technical Standards

### Shebang + PEP 723 Block
All Python scripts must use `uv run` for dependency management.
```python
#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "python-dotenv>=1.0",
#   "rich>=13.0",
# ]
# ///
```

### Portability Mandate
- **No hardcoded literals**: Paths, patterns, and URLs must be arguments or environment variables.
- **Pathlib only**: Use `pathlib.Path` for all file operations (OS-agnostic).
- **Subprocess**: Always use `timeout` and explicit `cwd`. Never use `shell=True`.
- **Env-first**: Use environment variables (via `python-dotenv`) for discoverable paths.

### Safety & Output
- **Dry Run**: Mandatory `--dry-run` flag for any script that modifies files or state.
- **Exit Codes**: `0`=success, `1`=error, `2`=usage.
- **Streams**: `stdout` for data (Markdown/text), `stderr` for logs and errors.
- **Token Efficiency**: Favor compact Markdown or plain text over verbose JSON.

## 3. Minimal Template
```python
import argparse
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="One-sentence purpose.")
    parser.add_argument("path", type=Path, help="Target path")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes")
    
    args = parser.parse_args()
    # Implementation...

if __name__ == "__main__":
    main()
```

## 4. Documentation (SKILL.md)
Every script must be documented in its parent `SKILL.md` with:
- One-sentence purpose (WHEN to use it)
- Usage example: `uv run script.py <args>`
- Argument table (Arg | Purpose)
