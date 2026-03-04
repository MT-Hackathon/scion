# Reference: Anchor Types

Anchor type definitions and navigation examples.

---

## Anchor Types

| Type | Purpose |
|------|---------|
| `ANCHORRULE` | Precedence rules (mandates) |
| `ANCHORSKILL` | Workflows/procedures |
| `ANCHORPERSONA` | Decision logic |
| `ANCHORCONTEXT` | Reference material |

## Navigation Examples

### Grep to locate anchor

```bash
grep "ANCHORSKILL-UI-DEBUGGING" src/
```

### Targeted read

```bash
# After finding line 150
read_file target_file="src/utils.ts" offset=145 limit=10
```

### Context extraction

```bash
grep -C 5 "ANCHORRULE-FOUNDATIONAL" .cursor/rules/001-foundational/RULE.mdc
```
