# Patterns: Environment Setup

Examples of correct environment setup and path usage.

---

## Python Environment Setup

### Correct Activation
```bash
conda activate Universal-API
python src/backend/main.py
```

### VS Code Configuration
`.vscode/settings.json`:
```json
{
  "python.defaultInterpreterPath": "/path/to/anaconda3/envs/Universal-API/bin/python"
}
```

## Node.js Environment Setup

### Correct Activation
```bash
nvm use 20
cd src/frontend
npm run dev
```

## Path Usage
Use `pathlib` with forward slashes:
```python
from pathlib import Path

project_root = Path(__file__).parent.parent
data_path = project_root / "data" / "input.csv"
```

### Anti-Pattern: Hardcoded Paths
```python
# BAD
data_path = "C:\\Users\\user\\projects\\data\\input.csv"
```
