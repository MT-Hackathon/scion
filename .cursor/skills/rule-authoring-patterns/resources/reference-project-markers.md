# Reference: Project-Specific Markers

Patterns that identify project-specific content requiring update during transfer.

---

## Rule Number Ranges

| Range | Classification | Transfer Action |
|-------|---------------|-----------------|
| 000-099 | Universal | Keep, strip project sections |
| 100-199 | Language-specific | Keep, strip project sections |
| 200-999 | Project-specific | Archive entirely |

---

## Content Markers

### Section Headers

| Marker | Location | Action |
|--------|----------|--------|
| `## Project Implementation` | Resource files | Clear content, keep header with placeholder |
| `### Project Information` | 001-foundational | Replace values with placeholders |

### Hardcoded References

| Pattern | Example | Replacement |
|---------|---------|-------------|
| Project name | `Universal-API` | `{{PROJECT_NAME}}` |
| Root path | `path/to/Universal-API` | `{{PROJECT_ROOT}}` |
| Conda env | `Universal-API` (as env name) | `{{ENV_NAME}}` |
| Backend path | `src/backend/main.py` | `{{BACKEND_ENTRY}}` |
| Frontend path | `src/frontend/` | `{{FRONTEND_DIR}}` |

---

## File Patterns

### Always Project-Specific (Archive)

```
.cursor/rules/2**/           # All 200+ rules
.cursor/rules/*/scripts/*_project_*.py  # Project-named scripts
```

### Contains Project Sections (Strip)

Files matching:

```
## Project Implementation
```

Typically found in:

- `examples-*.md`
- `reference-*.md`
- `guide-*.md`

### Project Information (Update)

```
.cursor/rules/001-foundational/RULE.mdc
```

Section: `### Project Information`

---

## Script Detection

The `scan-project-references.py` script detects:

1. **200+ rules**: Directories matching `^[2-9][0-9]{2}-`
2. **Project Implementation sections**: `grep "## Project Implementation"`
3. **Hardcoded project name**: `grep -i "universal-api"` (case-insensitive)
4. **Project paths**: `grep "src/backend\|src/frontend\|path/to/"`

---

## Placeholder Template

After transfer, placeholders follow this format:

```
{{PLACEHOLDER_NAME}}
```

Standard placeholders:

| Placeholder | Purpose | Example Value |
|-------------|---------|---------------|
| `{{PROJECT_NAME}}` | Project identifier | `MyNewProject` |
| `{{PROJECT_ROOT}}` | Absolute or relative root | `path/to/MyNewProject` |
| `{{ENVIRONMENT_TYPE}}` | Environment manager | `Anaconda`, `venv`, `nvm` |
| `{{ENV_NAME}}` | Environment name | `my-new-project` |
| `{{BACKEND_ENTRY}}` | Backend entry point | `src/api/main.py` |
| `{{BACKEND_DIR}}` | Backend directory | `src/api/` |
| `{{FRONTEND_DIR}}` | Frontend directory | `web/` |

---

## Exceptions

Content that should NOT be replaced during transfer:

| Location | Reason |
|----------|--------|
| `050-rule-authoring-patterns/` | Meta-documentation uses examples |
| Transfer guide examples | Illustrative, not functional |
| Archived rules | Already removed from active set |

---

## See Also

- [guide-transfer-workflow.md](guide-transfer-workflow.md) — Full workflow
- [checklist-transfer-preparation.md](checklist-transfer-preparation.md) — Quick checklist
