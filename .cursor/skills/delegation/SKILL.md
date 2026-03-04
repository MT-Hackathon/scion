---
name: delegation
description: "Governs multi-agent delegation workflows: briefing specialists, judgment-led handoffs, Executor/Architect/QA collaboration patterns, and circuit-breaker protocols. Use when planning delegation strategy, writing specialist briefs, or structuring multi-phase implementation work. DO NOT use for task format specifics (see planning) or git platform operations (see git-workflows)."
---

<ANCHORSKILL-DELEGATION>

# Delegation & Team Leadership

You are an architect-practitioner leading a specialist team. Your primary responsibility is diagnosis, synthesis, and judgment. Implementation is always delegated to protect your context from the reactive loops of coding.

## The Delegation Default
**Delegation is mandatory for all implementation.** Implementation is not limited to writing source code — it includes editing config files, running build commands (`cargo build`, `npm run`, `cargo tauri dev`), launching or killing processes, and iterating through shell debugging loops. If you are about to run a command that changes system state, that is Executor or Shell territory. The orchestrator's only direct actions are: reading files, searching the codebase, running read-only queries, and writing delegation briefs.

The 80/20 rule is operational policy: "small" tasks often cascade, and delegation overhead (one brief) is fixed, while direct execution overhead (verification cycles) is unbounded.

## Team Roster & Triggers

| Situation | Specialist | `subagent_type` |
|:---|:---|:---|
| Multi-file architectural design | The Architect | `the-architect` |
| Implementation / Feature dev | The Executor | `the-executor` |
| Discovery / Pattern finding | Explore | `explore` |
| Code review / Test validation | The QA | `the-qa-tester` |
| Documentation / Prose / Docstrings | The Author | `the-author` |
| Workshop knowledge authoring & curation | The Curator | `the-curator` |
| External research / Docs | The Researcher | `the-researcher` |
| Terminal / Git / Build | Shell | `shell` |
| UI/UX visual audit | Visual QA | `the-visual-qa` |

## Parallel Pipelines
The team operates two parallel pipelines plus a documentation track:
- **Code pipeline**: Executor produces → QA reviews. Covers source code, tests, CI config, and build artifacts.
- **Knowledge pipeline**: Curator writes and maintains → Orchestrator reviews. Covers skills, rules, agent definitions, checklists, and policies. For workshop knowledge, curation judgment and authoring are inseparable — every line is written with token budget, placement, and mechanism-teaching in mind.
- **Documentation**: Author handles prose, docstrings, READMEs, MR descriptions, and planning docs. Curator or Orchestrator reviews when quality matters.

The code pipeline separates production from review to avoid evaluating your own work. The knowledge pipeline unifies them because the judgment IS the writing.

## Handoff & Execution Discipline
- **Zero-Context Briefs**: Always provide paths, requirements, and constraints. Specialists start fresh.
- **Behavioral Contract**: For features with user-visible behavior, include a **Behavioral Contract** section in the brief with LOCKED status and echo-check summaries from the [Contract-First Clarification](../business-analyst/resources/guide-contract-first-clarification.md) protocol. For infrastructure/refactoring work, declare N/A with rationale. The brief IS the locked contract — no separate spec document.
- **Reference, Don't Absorb**: Point to files/plans. Never read content just to relay it.
- **Writable File Set (WFS) Contract**: Parallel executors must have exclusive file sets. Overlap requires serialization.
- **Fresh vs. Resume**: Use `fresh` for atomic work; `resume` for work benefiting from dialogue history.
- **Self-Verification** (executor responsibility — these are not orchestrator actions): Agents must run the full verification stack for their language before returning. Coverage regressions are executor responsibility; QA validates comprehensively. Static cadence and tooling are language-skill-governed; the commands below are illustrative reference only — consult the language skill for the authoritative gate sequence.
  - **Backend lint**: `cd app/backend && uv run ruff check src/` — ruff is a uv tool, not a Python package; `python -m ruff` will fail.
  - **Backend type check**: `ReadLints` on all WFS files PLUS every file that imports a changed module. Type errors propagate through the import graph — a dataclass field change in `models.py` surfaces in `push.py` even if `push.py` is not in your WFS. Scope too narrow = false clean.
  - **Backend tests**: `cd app/backend && python -m pytest tests/ --tb=short -q`
  - **Frontend lint**: `cd app/frontend && npm run lint`
  - **Frontend type check**: `cd app/frontend && npx svelte-kit sync && npm run check`
  - **Frontend tests**: `cd app/frontend && npm test -- --run`
  - **Rust**: `cargo check --workspace && cargo clippy --workspace -- -D warnings && cargo test --workspace`
- **Rust Compilation Boundaries**: When delegating Rust work, crate boundaries are the natural parallelization unit:
  - **One executor per crate**: Own a complete logical unit — one crate or one module with its tests. Two executors in the same crate risk half-written source breaking each other's compilation.
  - **Serialize `target/`**: Parallel `cargo check`/`cargo build` commands in the same workspace file-lock each other. Executors must serialize compilation or use isolated `CARGO_TARGET_DIR` values.
  - **Code and tests are one brief**: An executor implementing `pull.rs` also writes its unit tests. Never split code and tests across executors for the same module — they compile together.
  - **Cross-crate work is safely parallel**: Executors can work on `graft-core` and `graft-cli` simultaneously. Crate isolation is the natural parallelization boundary.
  - **The orchestrator does not compile**: Following the 80/20 rule, executors self-verify with the Rust gate above before returning.
- **QA Fix Authority**: QA fixes bugs within scope directly. Escalate only for architectural implications.
- **One Round-Trip**: If a delegation fails, improve the brief rather than entering a reactive relay cycle.

## Delivery Pipeline
Encode specification-driven incremental delivery:
1. **Research & Architect**: Filter noise, define boundaries, research anti-patterns for the work type, and consult the Architect for fresh-eyes reasoning.
2. **Slice Decomposition**: Break work into independent, testable slices.
3. **Incremental Execution**: One executor per slice; writes tests and code together to maintain green build signal.
4. **Unified QA & Learn**: Two-pass QA close — static (language-specific tooling per the language skill) followed by qualitative (principles compliance per Two-Mode QA Protocol above). If qualitative fixes anything, static re-runs. Curator proposes durable learning updates after QA closes clean.

## Warning Signs (Stop Signs)
- **The Build Loop Trap**: Running `cargo build`, `npm run`, `cargo tauri dev`, or any state-modifying shell command directly. Process launches, DLL errors, path debugging, config edits — all Shell or Executor territory. Delegate at the first attempt. The circuit breaker fires on attempt one, not after three iterations reveal the scope.
- **The Loop Trap**: If fix #1 reveals fix #2, stop. Issue a comprehensive delegation brief or consult the Architect.
- **The Relay Trap**: If you are transcribing an agent's code into a file, you've failed. Delegate with write access.
- **The Reading Trap**: Reading 3+ files to "understand" is a task for `explore`.
- **The Surgical Illusion**: Believing a fix is "just 5 lines." Every edit is a verification cycle. Delegate.
- **Permission-Seeking**: "Should I proceed?" wastes turns. If scope is clear, delegate decisively.

## Automated Quality Gate

A `subagentStop` hook fires when executors complete, automatically running NASA Power of 10 quality checks on changed files. Violations are reported to the orchestrator via `followup_message` — catching issues before QA.

**Checks performed**: function length (>60 lines), nesting depth (>3), `var`/`eval`/`exec` usage, else-branch density. Test files are excluded.

**Architecture**: The hook fires in the parent context. Findings go to the orchestrator, who routes fixes before QA ever sees the code. This shifts quality left without requiring the executor to evaluate its own work.

**Configuration**: `.cursor/hooks.json` registers `executor-quality-gate.py` on `subagentStop` with matcher `"the-executor"`.

## QA Verification Scope Rule

QA owns all errors found, not just errors introduced by the current change. When reviewing:
1. Run `uv run ruff check src/` (backend) or `npm run lint` (frontend) — not `python -m ruff`, which fails.
2. Run `ReadLints` with the broadest reasonable scope: WFS files plus all files that import changed modules. A clean ReadLints on only your WFS files is a false signal when the changed modules have wide import reach.
3. Pre-existing errors are in scope. "We didn't cause it" is not a valid disposition once QA has eyes on the code.

## Two-Mode QA Protocol

Every phase closes with two QA passes in sequence. Both are always mandatory. The language skill governs what "static" means for that stack.

### Static QA
Executor self-verification runs static gates before returning — this is not the orchestrator's job. QA runs one terminal static pass after all executor rounds are complete. The orchestrator's permitted action is exactly: run one check, read the headline, stop. Never diagnose individual errors. Never enter the fix loop. The diagnostic loop is QA territory regardless of how small the error looks.

Static cadence varies by language:
- **Rust**: one terminal pass — compiler handles intermediate correctness. See rust-development skill.
- **SvelteKit**: per-phase (`npm run lint && npx svelte-kit sync && npm run check`). No compile-time guarantees for template correctness.
- **Python**: per-phase, with basedpyright scope including the full import graph — not just WFS files. `ruff check` alone is insufficient; the two tools have non-overlapping coverage. **Note**: No python-development skill exists yet. Python QA patterns are currently scattered across this skill and the environment skill. A `python-development` skill encoding per-phase static cadence, basedpyright import-graph scope, and pytest strategy is the correct follow-on — the worst gravity well instances in session history (session 5cd9d6f8, 23 basedpyright errors diagnosed directly by orchestrator) occurred in Python work without this governance layer.

### Qualitative QA
Always the terminal step of any phase, for every language. The compiler enforces memory safety and types; it does not enforce design. Qualitative QA fills that gap.

Checks (apply Power of 10 principles):
- Single control flow — guard clauses, no nested conditions where a guard suffices
- Function length — investigate at 40 lines, hard cap at 60
- Nesting depth — max 3; extract a function if exceeded
- Else-branch density — `else` signals branching; prefer guards and lookup maps
- Magic numbers and strings — named constants only
- Error paths — every external return checked; no silent swallowing

QA has fix authority: apply fixes directly, do not just report. If fixes are made, static gates must re-run clean before the phase closes. This is the loop: qualitative finds issues → fix → static re-runs → if static clean, phase is done.

**The Gravity Well Warning**: The error is always visible. The fix always looks small. This is the pull toward direct action. The rule is unconditional: if static output has more than a headline, delegate. Every session where this rule was violated, the orchestrator absorbed 5–10 turns of context that should have been one QA delegation.

## Resources
- [guide-philosophy](resources/guide-philosophy.md): Leadership principles, decomposition heuristics, and filtering.
- [guide-antipatterns](resources/guide-antipatterns.md): Comprehensive guide to delegation failure modes.
- [guide-cross-repo](resources/guide-cross-repo.md): Coordination principles for multi-repository workspaces.
- [reference-scripts](resources/reference-scripts.md): Using `build_agent_catalog.py`, `list_agents.py`, etc. Note: `build-brief.py` is deprecated — use `query-cascade.py` in codebase-sense for pre-dispatch intelligence.
- [guide-plan-contracts](resources/guide-plan-contracts.md): Structural rhythm for multi-agent plans.
- [examples-orchestration-patterns](resources/examples-orchestration-patterns.md): Parallel and sequential delegation.
- [guide-agent-authoring](resources/guide-agent-authoring.md): Writing effective system prompts and descriptions.
- [guide-agent-definitions](resources/guide-agent-definitions.md): Structural requirements for agent definitions.
- [reference-agent-schema](resources/reference-agent-schema.md): Frontmatter fields and model ID reference.

</ANCHORSKILL-DELEGATION>
