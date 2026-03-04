# Plan: [Title]

**Slug**: `<slug>` (filename: `.cursor/plans/<slug>.md`)  
**Triggered by**: [what prompted this — user request, discovered issue, architecture decision]  
**Status**: Draft | Ready | Executing | Complete

---

## Context

[What problem does this solve? What is the current state and why is it insufficient? 2–4 sentences. Be specific enough that a future thread can understand the "why" without asking.]

---

## Requirements and Acceptance Criteria

Each requirement must be marked with a behavioral contract status:
- **LOCKED** — user-visible behavior changes; contract is confirmed before implementation begins
- **N/A** — pure infrastructure or refactoring; no user-visible behavioral change (state rationale)

| # | Requirement | Status | Notes |
|---|-------------|--------|-------|
| R1 | | LOCKED / N/A | |
| R2 | | LOCKED / N/A | |

---

## Cascade Analysis

Three orders of effect. One identified risk minimum per order, or state "unknown" with a verification step.

**Order 1 — Direct dependents** (impacted immediately by this change):
- Risk: 

**Order 2 — Consequential modules** (likely to require coordinated change):
- Risk: 

**Order 3 — Conditional failures** (if assumptions break):
- Risk: 

---

## Risk Inventory

| Risk | Likelihood | Impact | Verification Step |
|------|------------|--------|-------------------|
| | | | |

---

## Delegation Structure

| Phase | Agent | Brief Summary | Handoff Criteria | Verification Command |
|-------|-------|---------------|------------------|----------------------|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |

---

## Phase Detail

### Phase 1: [Agent] — [Description]

**Files in scope**:
- `path/to/file.ext:line-range`

**Task**:
[Specific instructions. No vague language — no "consider", "maybe", "might", "TBD". Every step executable without sub-planning.]

**Before/after** (for code changes):
```
// Before
// After
```

**Verification**:
```
[exact command]
```

**Handoff criteria**: [What must be true before Phase 2 begins]

---

### Phase 2: [Agent] — [Description]

[repeat structure]

---

## Notes and Open Questions

[Anything resolved during design that shouldn't be re-litigated during build. Architectural decisions, rejected alternatives, constraints discovered.]
