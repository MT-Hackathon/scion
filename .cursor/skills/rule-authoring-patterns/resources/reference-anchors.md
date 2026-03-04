# Anchor Naming Convention

Anchor names derive from folder names in UPPER-KEBAB-CASE:

- `environment/` → `<ANCHORSKILL-ENVIRONMENT>`
- `100-constitution-python/` → `<ANCHORSKILL-CONSTITUTION-PYTHON>`

## Rules

- One anchor per rule (in RULE.mdc)
- Deprecated rules should NOT have anchors
- Anchor must be unique across all rules

## Deprecation Pattern

When consolidating rules, mark the old rule as deprecated:

1. Update frontmatter: `description: "DEPRECATED - Consolidated into {rule}. DO NOT USE."`
2. Remove the anchor entirely
3. Keep minimal redirect content pointing to new location
4. Remove after grace period

### Example Deprecated Rule

```markdown
---
description: "DEPRECATED - Consolidated into 100-constitution-core. DO NOT USE."
alwaysApply: false
---

# DEPRECATED

This rule has been consolidated into [100-constitution-core](../100-constitution-core/RULE.mdc).
```
