# Guide: Git Issues as Requirements

Git issues and markdown requirements are dual sources of truth. This guide ensures git issues carry the same rigor as Feature Card specifications.

---

## Issue Structure

### Title Convention

```
[F-XX] Brief description of the feature or enhancement
```

Examples:
- `[F-01] Add "My Requests" list for requesters`
- `[F-03] Implement separation of duty check in approval flow`
- `[F-07] Improve permission denial UX with meaningful error messages`
- `[NEW] Audit log viewer for system administrators`

### Body Template

```markdown
## Context
Which Feature Card does this implement or extend?
- Feature Card: F-XX (link to specific section in 12-feature-interaction-map.md)
- Related issues: #nn, #mm

## Problem
What gap or deficiency does this address?
(Reference specific success criterion or acceptance test from the Feature Card)

## Scope
What specific aspects of the Feature Card are in scope for this issue?
- [ ] Success criterion 1: [description]
- [ ] Success criterion 3: [description]

## Acceptance Criteria

GIVEN [precondition]
WHEN [action]
THEN [outcome]

GIVEN [precondition]
WHEN [action]
THEN [outcome]

## Out of Scope
What is explicitly NOT addressed by this issue?

## Dependencies
- Requires #nn to be completed first
- Blocked by: [description]
```

---

## Labels

### Feature Card Labels
Every issue MUST have a Feature Card label:
- `F-01` through `F-14` for existing capabilities
- `F-NEW` for capabilities not yet in doc 12 (Feature Card creation required before implementation)

### Type Labels
- `feature` — New capability or sub-capability
- `enhancement` — Improvement to existing capability
- `bug` — Defect in existing capability
- `gap` — Missing layer in an existing feature (e.g., "backend exists but no UI")
- `a11y` — Accessibility deficiency

### Priority Labels
- `critical` — Blocks core workflow (Flows A-D)
- `high` — Significantly impacts user experience
- `medium` — Reduces confidence or reliability
- `low` — Polish or future consideration

### Layer Labels (optional, for tracking completeness)
- `backend` — Requires backend changes
- `frontend` — Requires frontend changes
- `tests` — Requires new or updated tests
- `docs` — Requires documentation updates

---

## Milestones

Use milestones to group issues into releases or sprints:
- Milestone name should indicate the release or time period
- Each milestone should have a target date
- The milestone description should reference which end-to-end flows (A-D) should be verified

---

## Workflow: From Issue to Done

```
1. PM creates issue with body template
2. PM adds labels (Feature Card, type, priority)
3. PM assigns to milestone
4. Dev picks up issue
5. Dev reads the linked Feature Card for full context
6. Dev implements against the acceptance criteria
7. Dev creates PR with: "Implements #issue-number" in description
8. PR review verifies acceptance criteria
9. Merge → CI tests pass
10. PM verifies user journey
11. Issue closed → Feature Card matrix updated
```

---

## When a Git Issue Introduces a NEW Feature

If the issue describes a capability not currently in `12-feature-interaction-map.md`:

1. **STOP** — Do not start implementation
2. Create a new Feature Card (F-15, F-16, etc.) in doc 12 using the existing format
3. Include: Actors, Entry Points, User Journey, Screen Inventory, Success Criteria, Acceptance Tests, Dependencies, Implementation Status
4. Update the issue to reference the new Feature Card
5. Then proceed with implementation

This ensures every line of code traces to a documented requirement.

---

## Converting Existing Issues

For issues already in the tracker without this structure:

1. Add the Feature Card label based on which capability the issue relates to
2. Add acceptance criteria in Given/When/Then format
3. Add type and priority labels
4. Link to the Feature Card section in the issue body
5. No need to rewrite the entire issue — augment with traceability

---

## Anti-Patterns

| Anti-Pattern | Fix |
|-------------|-----|
| Issue title: "Fix the thing" | Use `[F-XX] Specific description` |
| No acceptance criteria | Add Given/When/Then before implementation starts |
| No Feature Card link | Add the label and body reference |
| "Implement everything in F-03" | Break into focused issues: one per success criterion or sub-feature |
| Issue stays open after merge | Close with verification comment |
| Feature Card not updated after implementation | Update matrix in same PR or follow-up |
