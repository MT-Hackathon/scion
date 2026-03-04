# Guide: Rule Transfer Workflow

Complete workflow for transferring rules to a new project.

---

## Overview

This is an AI-assisted workflow. Scripts provide scanning and validation; the AI performs the actual transfer work with human confirmation.

---

## Phase 1: Pre-Transfer Scan

Run the scanner to understand current state:

```bash
python .cursor/skills/rule-authoring-patterns/scripts/scan-project-references.py
```

Review the output:

- Count of 200+ rules to archive
- Files with `## Project Implementation` sections
- Hardcoded project references to update

---

## Phase 2: Archive Project-Specific Rules

### Step 2.1: Create Archive Directory

Create dated archive at project root (NOT inside .cursor/rules/):

```
{project-root}/archived-rules-YYYY-MM-DD/
```

### Step 2.2: Move 200+ Rules

Move all rules in the 200-999 range to the archive:

```
archived-rules-YYYY-MM-DD/
  201-packages/
  210-ui-core/
  215-ui-canvas/
  220-svelte-ui/
  225-ui-security/
  250-data-contract/
  260-rate-limit-principles/
  265-integration-testing/
  267-rbac-authorization/
  270-error-architecture/
  285-fullstack-workflow/
  290-data-mapping-principles/
```

### Step 2.3: Update Cross-References

Remove or comment out cross-references in 000-199 rules that point to archived 200+ rules.

Check these files for dead links:

- `*/resources/cross-references.md`
- Rule manifests that reference 200+ rules

---

## Phase 3: Strip Project Implementation Sections

For each file with `## Project Implementation` sections (in 000-199 range):

1. Locate the section
2. Replace content with placeholder comment:

```markdown
## Project Implementation

<!-- Project-specific implementation details go here -->
<!-- Populate when adapting to new project -->
```

1. Preserve the `## Pattern` section above it (this is portable)

---

## Phase 4: Update Foundational Project Information

Update `001-foundational/RULE.mdc` Project Information section:

**Before (project-specific):**

```markdown
### Project Information
- **Environment**: Node.js 22+ via nvm, npm for package management.
- **Root Directory**: `./procurement-web`
- **Project Name**: `procurement-web`
- **Frontend**: Angular 21 with Angular Material (`src/app/`)
- **Testing**: Vitest with jsdom
- **Auth**: Okta (@okta/okta-angular)
```

**After (placeholders):**

```markdown
### Project Information
- **Environment**: {{ENVIRONMENT_TYPE}} — e.g., Anaconda (`conda activate {{ENV_NAME}}`), venv, nvm
- **Root Directory**: {{PROJECT_ROOT}}
- **Project Name**: {{PROJECT_NAME}}
- **Backend**: {{BACKEND_ENTRY}} (if applicable)
- **Frontend**: {{FRONTEND_DIR}} (if applicable)
```

---

## Phase 5: Clean Up Hardcoded References

Search and update remaining hardcoded project references in 000-199 rules:

| Pattern | Action |
|---------|--------|
| `Universal-API` (project name) | Replace with `{{PROJECT_NAME}}` or remove |
| `path/to/Universal-API` | Replace with `{{PROJECT_ROOT}}` |
| `src/backend/` paths | Replace with `{{BACKEND_DIR}}/` or remove |
| `src/frontend/` paths | Replace with `{{FRONTEND_DIR}}/` or remove |

**Exception:** Keep references in:

- This transfer guide (as examples)
- The 050 rule itself (meta-documentation)

---

## Phase 6: Validation

Run the validation script:

```bash
python .cursor/skills/rule-authoring-patterns/scripts/validate-transfer-ready.py
```

Confirm:

- [ ] No 200+ rules in `.cursor/rules/`
- [ ] No populated `## Project Implementation` sections
- [ ] Project Information has placeholders
- [ ] No dead cross-references

---

## Adaptation Workflow (New Project)

When adapting to a new project:

### Step A: Gather Project Information

Collect:

- Project name
- Root directory path
- Environment type (conda, venv, nvm, etc.)
- Backend entry point (if any)
- Frontend directory (if any)

### Step B: Replace Placeholders

Update `001-foundational/RULE.mdc` with actual values.

### Step C: Populate Project Implementation Sections

As you learn project patterns, populate `## Project Implementation` sections in resource files.

### Step D: Create Project-Specific Rules

Create new 200+ rules as needed for:

- Project-specific UI patterns
- Domain-specific workflows
- Project integrations

---

## Archive Recovery

If you need to reference archived rules:

```bash
# View archived rules
ls archived-rules-YYYY-MM-DD/

# Restore a specific rule
mv archived-rules-YYYY-MM-DD/210-ui-core .cursor/rules/
```

---

## See Also

- [checklist-transfer-preparation.md](checklist-transfer-preparation.md) — Quick reference checklist
- [reference-project-markers.md](reference-project-markers.md) — What constitutes project-specific content
