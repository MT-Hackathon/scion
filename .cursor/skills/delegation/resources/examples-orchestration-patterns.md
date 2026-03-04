# Orchestration Patterns & Examples

## Pattern Definitions

### Pattern 1: Parallel Design Pattern

Replacing strict TDD, this pattern shifts the quality gate from "test passage" to "collaborative review." It prevents the "tests aren't always right" trap by drafting both tests and implementation concurrently.

1. **Parallel Drafting**: `QA` drafts tests while `Executor` drafts implementation.
2. **Unified Review**: `Architect` (or Orchestrator) reviews both drafts for alignment and spec compliance.
3. **Refine**: Both agents refine their work based on review feedback.
4. **Final Verification**: `QA` verifies the final state with full suite execution.

### Pattern 2: Parallel Routing

When multiple independent problems exist, route one specialist per domain simultaneously.

- **Parallelizable combinations**:
  - Multiple `explore` for different codebase areas.
  - Multiple `Executor` for independent file sets.
  - `QA` + `Author` simultaneously (verifying vs. documenting).

**Constraint**: Never parallelize agents editing the same files or tasks with strict dependencies.

### Pattern 3: Cross-Repository Orchestration

For features spanning multiple repositories, use repo-specific dispatches to prevent tool conflicts and context pollution.

1. **Parallel Exploration**: Dispatch `explore` to each repository independently.
2. **Code-First Contracting**: Define backend contracts (DTOs, OpenAPI annotations) before frontend integration begins.
3. **Independent Verification**: Each repository is gated by its own local test suite.

### Pattern 4: Escalation Chain

Tasks should be routed based on complexity and scope.

- **Executor**: Standard to complex implementation (single feature, multi-file).
- **Architect**: Design decisions, plan verification, or architectural changes (NOT implementation).

### Pattern 5: Research-Before-Implementation

For new or high-risk architectural patterns:

1. **Research**: Parallel agents investigate and write findings to `.cursor/handoffs/raw/agent-{id}.md`.
2. **Synthesis**: `Author` reads raw files and writes `.cursor/handoffs/{topic}.md`.
3. **Execution**: Implementation agents are briefed by referencing the handoff file path.

---

## Example 1: Full Feature Workflow (Parallel Design)

**Scenario**: User requests "Add user role validation to the auth flow"

### Phase 1: Context Gathering

```
Route: explore (thoroughness: medium)
Prompt: "Execute todo #auth-exploration from @plan.md"
working_directory: "frontend-repo"

Result: Identified files:
- src/app/services/auth.service.ts
- src/app/guards/auth.guard.ts
- src/app/models/user.model.ts
```

### Phase 2: Parallel Drafting

```
Agent 1: QA
Prompt: "Draft unit tests for user role validation in src/app/guards/auth.guard.ts. Reference @plan.md for specs."
working_directory: "frontend-repo"

Agent 2: Executor
Prompt: "Draft the implementation for role validation in src/app/services/auth.service.ts and auth.guard.ts. Reference @plan.md."
working_directory: "frontend-repo"
```

### Phase 3: Unified Review

```
Route: Architect
Prompt: "Review the drafted tests and implementation for role validation. Ensure alignment and spec compliance."
working_directory: "frontend-repo"

Result: Review notes for alignment on edge case: "Admin role should bypass restriction."
```

### Phase 4: Refinement & Verification

```
Route: Executor
Prompt: "Apply review feedback to implementation: ensure Admin bypass is included."
working_directory: "frontend-repo"

Route: QA
Prompt: "Verify final implementation against test suite and check lints."
working_directory: "frontend-repo"
```

---

## Example 2: Parallel Codebase Exploration

**Scenario**: User asks "How do API endpoints, authentication, and database access work in this app?"

Launch three explore agents simultaneously:

```
Agent 1: explore (thoroughness: medium)
Prompt: "Analyze API controller patterns in backend-repo/src/..."
working_directory: "backend-repo"

Agent 2: explore (thoroughness: medium)
Prompt: "Analyze auth middleware and guards in frontend-repo/src/app/..."
working_directory: "frontend-repo"

Agent 3: explore (thoroughness: medium)
Prompt: "Analyze data repository patterns in backend-repo/src/..."
working_directory: "backend-repo"
```

---

## Example 3: Cross-Repo Feature Implementation

**Scenario**: "Add a new API endpoint for approval history and display it in the frontend"

### Phase 1: Parallel Exploration
```
Agent 1: explore
Prompt: "Map existing history/audit patterns in the backend."
working_directory: "backend-repo"

Agent 2: explore
Prompt: "Map existing history/table display patterns in the frontend."
working_directory: "frontend-repo"
```

### Phase 2: Contract Definition (Code-First)
```
Route: Author
Prompt: "Define DTO records and API contract annotations for a new approval history endpoint in backend-repo/src/..."
working_directory: "backend-repo"
```

### Phase 3: Parallel Drafting
```
Agent 1: Executor (API)
Prompt: "Draft approval history API implementation and tests in backend-repo. Reference the contract definitions from Phase 2."
working_directory: "backend-repo"

Agent 2: Executor (UI)
Prompt: "Draft UI component scaffold and tests in frontend-repo. Reference the approval-history DTO/response shape from backend-repo and keep hand-written models aligned."
working_directory: "frontend-repo"
```

### Phase 4: Review & Refine
```
Route: Architect
Prompt: "Review both API and UI drafts for contract alignment."
working_directory: "frontend-repo"
```

### Phase 5: Cross-Repo Verification
```
Agent 1: QA
Prompt: "Verify backend implementation."
working_directory: "backend-repo"

Agent 2: QA
Prompt: "Verify frontend implementation."
working_directory: "frontend-repo"
```

---

## Example 4: Task Sizing Strategies

**Scenario**: "Implementing user preferences feature"

### Strategy A: Whole-Feature Dispatch (Preferred for Clarity)
Use when requirements and acceptance criteria are explicit.
```
Route: Executor
Prompt: "Implement the user preferences feature across the stack: API service, UI panel, and persistence. Reference @plan.md for requirements."
```

### Strategy B: Decomposed Dispatch (Preferred for Concurrency/Risk)
Use when you want parallel progress across streams or fresh eyes on different components.
```
Task 1: Executor (API)
Prompt: "Implement UserPreferences API logic (service + repository) in backend-repo/src/..."
working_directory: "backend-repo"

Task 2: Executor (UI)
Prompt: "Implement the preferences panel component and associated styles in frontend-repo/src/app/features/"
working_directory: "frontend-repo"
```

**Tradeoff**: Strategy A minimizes coordination overhead and preserves feature coherence. Strategy B maximizes throughput via concurrency and provides fresh-eye verification at each integration point.

---

## Example 5: QA Batching with Domain Isolation

**Scenario**: QA finds 12 lint errors, 3 test failures, and 1 complex flaky test.

### 1. Triage
The Orchestrator identifies that lint errors are mechanical, 3 test failures are related to a recent refactor, and the flaky test is an environment issue.

### 2. High-Coherence Batching (Mechanical Fixes)
```
Agent 1: Executor
Prompt: "Fix all 12 lint errors in frontend-repo/src/app/... Reference @lint-report.json."
working_directory: "frontend-repo"
```

### 3. Isolated Investigation (Hard/Unrelated Issue)
```
Agent 2: Executor
Prompt: "Investigate and fix the flaky test in AuthGuard. You have room to research environment timing issues."
working_directory: "frontend-repo"
```

### 4. Sequential Verification
Once lints are clean and the flake is understood, the Orchestrator dispatches a final `QA` agent to fix the remaining 3 test failures, ensuring they aren't masked by noise.

---

## Example 6: Documentation Synthesis

**Scenario**: New service implemented, needs documentation.

```
Route: Author
Prompt: "Read frontend-repo/src/app/services/notification.service.ts and generate JSDoc and a usage guide in the feature README."
working_directory: "frontend-repo"
```

---

## Example 7: Escalation from Initial Scope Guess

**Scenario**: Initial scope looked small, but delegation revealed hidden complexity.

```
Response: "ESCALATION REQUIRED. This task exceeds initial scope assumptions:
- Requires changes to 4 files in backend-repo.
- New database migration needed.
- Complex validation logic discovery required.

Recommend: Route to Executor."
```

---

## Resources

- **guide-antipatterns.md** — Common mistakes and what wastes tokens
- **guide-plan-contracts.md** — Contract format for plan sections
- **[../SKILL.md](../SKILL.md)** — Foundational orchestration principles
