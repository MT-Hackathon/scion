# Checklist: Transfer Preparation

Quick reference for rule transfer workflow.

---

## Pre-Transfer

- [ ] Run `scan-project-references.py` and review output
- [ ] Confirm archive location: `{project-root}/archived-rules-YYYY-MM-DD/`
- [ ] Identify 200+ rules to archive (count from scan)
- [ ] Note files with `## Project Implementation` sections

---

## Archive Phase

- [ ] Create dated archive directory at project root
- [ ] Move all 200-999 rules to archive
- [ ] Verify `.cursor/rules/` contains only 000-199 rules

---

## Strip Phase

- [ ] Clear `## Project Implementation` sections in 000-199 rules
- [ ] Replace content with placeholder comment
- [ ] Preserve `## Pattern` sections (these are portable)

---

## Update Phase

- [ ] Update `001-foundational/RULE.mdc` Project Information with placeholders:
  - `{{PROJECT_NAME}}`
  - `{{PROJECT_ROOT}}`
  - `{{ENVIRONMENT_TYPE}}` / `{{ENV_NAME}}`
  - `{{BACKEND_ENTRY}}` (if applicable)
  - `{{FRONTEND_DIR}}` (if applicable)
- [ ] Search for remaining hardcoded project references
- [ ] Update or remove project-specific paths

---

## Cross-Reference Cleanup

- [ ] Check `*/resources/cross-references.md` for dead links to 200+ rules
- [ ] Remove or comment out references to archived rules
- [ ] Update any manifest sections that list 200+ rules

---

## Validation

- [ ] Run `validate-transfer-ready.py`
- [ ] All checks pass:
  - No 200+ rules in `.cursor/rules/`
  - No populated `## Project Implementation` sections
  - Project Information has placeholders

---

## Post-Transfer (New Project)

- [ ] Replace placeholders with actual project values
- [ ] Create new 200+ rules as project patterns emerge
- [ ] Populate `## Project Implementation` sections as needed

---

## See Also

- [guide-transfer-workflow.md](guide-transfer-workflow.md) — Detailed workflow steps
- [reference-project-markers.md](reference-project-markers.md) — What to look for
