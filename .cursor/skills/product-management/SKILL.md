---
name: product-management
description: "Governs feature completeness, requirements traceability, and acceptance criteria. Use when implementing features, writing acceptance tests, verifying feature completeness, mapping requirements to code, or working with git issues as requirements. DO NOT use for code architecture (see planning) or test implementation patterns (see angular-testing)."
---

<ANCHORSKILL-PRODUCT-MANAGEMENT>

# Product Management

Ensures features ship complete, traceable, and verified against business requirements.

## Contents

- [When to Use This Skill](#when-to-use-this-skill)
- [Core Workflow](#core-workflow)
- [Scripts](#scripts)
- [Resources](#resources)
- [Cross-References](#cross-references)

## When to Use This Skill

- Starting work on a feature (find the Feature Card first)
- Writing acceptance criteria or tests
- Verifying a feature is complete before marking done
- Converting a git issue into a trackable requirement
- Reviewing feature completeness across the system
- Prioritizing gaps for the next development cycle
- Managing requirements changes or scope adjustments

## Core Workflow

### 1. Before Starting a Feature

```
Feature Card Lookup → Acceptance Criteria Review → Dependency Check → Implement
```

1. Find the Feature Card in `docs/requirements/12-feature-interaction-map.md` (F-01 through F-14)
2. If working from a git issue, verify it links to a Feature Card ID
3. Review success criteria — these are your definition of done
4. Check dependencies — ensure prerequisite features exist
5. If no Feature Card exists, create one before implementing

### 2. During Implementation

Use the **Feature Completeness Checklist** for each feature:

| Check | Question |
|-------|----------|
| Requirement | Does this feature trace to a Feature Card or git issue? |
| User Journey | Can a user complete the full journey described in the Feature Card? Verified via Visual QA journey audit (`resources/journeys/journey-*.md`). A feature with no journey file has an unverified user path. |
| Happy Path | Does the primary scenario work end-to-end? |
| Error Path | Do validation failures show clear messages? |
| Permission Path | Are unauthorized users blocked with meaningful feedback? |
| Accessibility | Keyboard navigable? Screen reader compatible? Sufficient contrast? |
| Audit | Are state changes and field edits recorded? |
| Tests | Do automated tests cover the acceptance criteria? |
| Domain | Do tests cover complex PWMM state transitions (thresholds, parallel gates, loopbacks), not just happy-path CRUD? |

### 3. After Implementation

1. Walk through each acceptance test (Given/When/Then) manually or with automation
2. Verify the feature in its end-to-end flow (reference Flows A-D in doc 12)
3. Update the Implementation Completeness Matrix
4. Run the `verify-feature-completeness.py` script to check coverage

## Scripts

### verify-feature-completeness.py

Scans the codebase to assess implementation completeness for a specific feature.

`uv run --script scripts/verify-feature-completeness.py <feature-id> [--verbose]`

| Arg | Purpose |
|-----|---------|
| `<feature-id>` | Feature Card ID (e.g., F-01, F-03) |
| `--verbose` | Show detailed file matches |

**What it checks:**
- Backend: Controllers, services, DTOs for the feature domain
- Frontend: Components, services, routes for the feature
- Tests: Test files that reference the feature's components
- Gaps: Missing layers (e.g., backend exists but no frontend component)

### map-requirements-to-code.py

Maps Feature Card success criteria to implemented code locations.

`uv run --script scripts/map-requirements-to-code.py [--feature <id>] [--all] [--format markdown|json]`

| Arg | Purpose |
|-----|---------|
| `--feature <id>` | Map a specific feature (e.g., F-01) |
| `--all` | Map all features |
| `--format` | Output format (default: markdown) |

**Output:** For each success criterion, shows the code files that implement it (or "NOT FOUND" for gaps).

## Resources

- [Acceptance Criteria Template](resources/template-acceptance-criteria.md) — Standard format for writing acceptance criteria
- [Feature Completeness Checklist](resources/checklist-feature-completeness.md) — Detailed verification checklist per feature type
- [Definition of Done](resources/reference-definition-of-done.md) — What "done" means for each layer
- [Git Issue Requirements Guide](resources/guide-git-issue-requirements.md) — How to write git issues that serve as requirements
- [Change Management Guide](resources/guide-change-management.md) — How to handle requirements changes, scope adjustments, and implementation-discovered gaps

## Cross-References

- [Rootstock System Rule](../../rules/005-rootstock-system/RULE.mdc) — Always-on safety invariants
- [Planning Skill](../planning/SKILL.md) — Decomposition and delegation patterns
- [Angular Testing Skill](../angular-testing/SKILL.md) — Test implementation patterns
- [Accessibility Skill](../accessibility/SKILL.md) — 508 compliance requirements

</ANCHORSKILL-PRODUCT-MANAGEMENT>
