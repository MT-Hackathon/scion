# Examples: Planning Patterns

Examples of prescriptive vs vague planning.

---

## Good: Prescriptive Plan

- "Update `src/auth.ts` line 45 to use `newValidator()` instead of `oldValidator()`."
- "Verify with `pytest tests/test_auth.py`."

## Bad: Vague Plan

- "Fix the auth bug."
- "Update some files."

## Include Script Verification

```markdown
## Verification
1. Run `.cursor/rules/050-rule-authoring-patterns/scripts/validate-scaffolding-compliance.py`
2. Verify output shows 0 errors
```
