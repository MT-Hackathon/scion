---
name: planning
description: "Defines delegation todo format and handoff contracts for specialist agents. Use when writing task briefs for Executor, Author, QA, or Architect agents, or decomposing implementation work into delegatable units. DO NOT use for delegation philosophy and patterns (see delegation) or git platform workflows (see git-workflows)."
---

<ANCHORSKILL-PLANNING>

# Planning & Decomposition

## Core Principles

- **Reference, don't regenerate**: Point peers to the plan file rather than duplicating content in consultation prompts. Peers can read files; let them read the plan to save tokens and prevent drift.
- **Test-first planning**: TDD is a planning decision. Define success with a failing test before writing code. Focus on services, logic, and guards. Reference the [angular-testing](../angular-testing/SKILL.md) skill for templates.
- **Reviewer gate**: Plans with 3+ implementation steps should be validated by **The QA** (`[the-qa-tester]`), who catches blind spots AND fixes what it finds. For plans with architectural ambiguity or cross-domain scope, consult **The Architect** (`[the-architect]`) — the strongest planning model available, and your primary loop-breaker when fixes cascade.
- **Circuit breaker protocol**: Adhere to the protocol defined in the [Foundational Mandates](../../rules/001-foundational/RULE.mdc). One-shot execution or comprehensive delegation — never a reactive loop. When a fix cascades, stop and consult the Architect before the next attempt.
- **Anti-pattern recon**: Before implementing, actively research failure modes and anti-patterns for the type of work being planned — not just best practices. Use the Researcher for unfamiliar domains. Document identified anti-patterns as explicit "avoid" items in the plan and in delegation briefs. Knowing what goes wrong is as valuable as knowing what goes right; catching pitfalls before implementation is cheaper than discovering them during review.
- **Cognitive load mandate**: Plans must eliminate execution-time improvisation; another agent should be able to execute without making architectural decisions mid-flight.

## Mandatory Plan Validation Checklist
Before submitting any plan:
- Every file path includes a line range (for example, `src/service.py:45-67`).
- Every code change includes before/after snippets.
- Every step includes a verification command using the correct invocation (see Verification Commands below).
- No vague language (`consider`, `maybe`, `might`, `possibly`, `TBD`, `?`).
- No step is so large that it requires sub-planning to execute.
- Behavioral contract status declared for each implementation slice: **LOCKED** (if user-visible behavior changes) or **N/A** with rationale (if pure infrastructure/refactoring). See [Contract-First Clarification](../business-analyst/resources/guide-contract-first-clarification.md) for trigger rules and protocol.

## Verification Commands (Canonical Invocations)

Always use these exact forms in executor and QA briefs. Wrong invocations silently skip quality checks.

| Check | Command | Notes |
|---|---|---|
| Backend style/lint | `cd app/backend && uv run ruff check src/` | `python -m ruff` fails — ruff is a uv tool, not a package |
| Backend type check | `ReadLints` on WFS + files importing changed modules | Import-graph scope; narrow scope = false clean |
| Backend tests | `cd app/backend && python -m pytest tests/ --tb=short -q` | |
| Frontend lint | `cd app/frontend && npm run lint` | Runs eslint + stylelint |
| Frontend type check | `cd app/frontend && npx svelte-kit sync && npm run check` | |
| Frontend tests | `cd app/frontend && npm test -- --run` | Requires Playwright Chromium pre-installed |

## Mandatory Test Quality Gates
1. **Behavior validated**: tests assert logic outcomes, not vague "works" statements.
2. **State verification**: include initial -> action -> expected state with concrete values.
3. **Edge cases explicit**: include none/empty/boundary conditions.
4. **Guard clauses tested**: each guard has a failing-input test case.

## Forbidden Test Patterns
For anti-patterns that invalidate implementation plans (tautological tests, type-only checks, magic numbers), see the **Anti-Patterns to Flag** section in [checklist-test-quality.md](../angular-testing/resources/checklist-test-quality.md).

## Peer-Consultation Todos

Use this convention for actionable, self-sufficient todos:

```
[agent] files: action → return
```

| Component | Purpose | Example |
|-----------|---------|---------|
| `[agent]` | Persona to consult | `[the-executor]`, `[the-author]` |
| `files:` | Scope (paths) | `src/app/auth.service.ts:45-67:` |
| `action` | Task or starting point | `Add token refresh logic` |
| `→ return` | Output constraint | `→ summary of changes` |

### Example
```yaml
- id: implement-refresh
  content: "[the-executor] src/app/auth.service.ts:45-67: Add token refresh with 3-retry exponential backoff → confirmation"
  status: pending
```

## Todo Granularity

Match todo granularity to agent capability. The Executor handles feature-level multi-file work — use feature-level todos, not function-level, unless concurrency or fresh eyes justify finer decomposition.

## Resources

- [examples-plan-structure.md](resources/examples-plan-structure.md) — Agent-consultation format and good/bad examples.
- [checklist-plan-validation.md](resources/checklist-plan-validation.md) — Required pre-submission validation and test-quality checks.
- [cross-references.md](resources/cross-references.md) — Links to orchestration, testing, and documentation skills.
- [Reference: Requirements Methodology](resources/reference-requirements-methodology.md)

</ANCHORSKILL-PLANNING>
