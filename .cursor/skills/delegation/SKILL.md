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
- **Self-Verification** (executor responsibility — these are not orchestrator actions): Language-specific. Rust is the exception — see Rust Protocol below. All other stacks:
  - **Backend lint**: `cd app/backend && uv run ruff check src/` — ruff is a uv tool, not a Python package; `python -m ruff` will fail.
  - **Backend type check**: `ReadLints` on all WFS files PLUS every file that imports a changed module. Type errors propagate through the import graph — a dataclass field change in `models.py` surfaces in `push.py` even if `push.py` is not in your WFS. Scope too narrow = false clean.
  - **Backend tests**: `cd app/backend && python -m pytest tests/ --tb=short -q`
  - **Frontend lint**: `cd app/frontend && npm run lint`
  - **Frontend type check**: `cd app/frontend && npx svelte-kit sync && npm run check`
  - **Frontend tests**: `cd app/frontend && npm test -- --run`
- **Rust Execution Protocol** (non-negotiable — cargo collisions on Windows destroy drives):
  - **Executors write code only.** Do NOT run `cargo check`, `cargo clippy`, `cargo build`, or any cargo command. This is an absolute rule, not a preference.
  - **All Rust compilation is owned by a single QA agent** dispatched after all executors complete. One cargo process at a time. QA runs `cargo check`, then `cargo clippy`, then relevant tests — in a single sequential agent.
  - **One logical contract per executor brief**: One struct, one module, one command handler, one feature. Narrow scope produces high-quality output from a fast model; wide scope produces over-engineered output from any model.
  - **One executor per crate boundary**: If work touches two crates, use two sequential executors or one executor with explicit file ownership. Executors in the same crate must have exclusive file sets — partial writes break QA's compilation run.
  - **Rationale**: Windows NTFS hard link contention + Defender scanning causes a death spiral when two cargo processes share `target/`. The system grinds, processes hang, `taskkill` itself hangs. There is no safe parallel cargo on Windows.
- **QA Fix Authority**: QA fixes bugs within scope directly. Escalate only for architectural implications.
- **One Round-Trip**: If a delegation fails, improve the brief rather than entering a reactive relay cycle.

## Delivery Pipeline
Encode specification-driven incremental delivery:
1. **Research & Architect**: Filter noise, define boundaries, research anti-patterns for the work type, and consult the Architect for fresh-eyes reasoning.
2. **Slice Decomposition**: Break work into slices where each slice has a single coherent concern and fully specified contracts. File count is not the constraint — decision density is. A brief covering 3–4 files of the same concern with tight contracts is better than 3 single-file briefs with vague direction. The goal: no architectural decisions remain open inside the brief for the executor to invent.
3. **Parallel Execution (non-Rust) / Sequential Execution (Rust)**: For non-Rust stacks: one executor per slice with non-overlapping file sets, can run in parallel. For Rust: executors write code only (no cargo), can run in parallel with non-overlapping file sets — all compilation is deferred to a single QA pass.
4. **Unified QA & Learn**: Two-pass QA close — **Gate A** (mechanical correctness + test quality: compilation, lint, test wiring, test anti-pattern audit) then **Gate B** (holistic judgment: "is this actually good code?", security boundary enforcement, design fitness). Gate A has fix authority for mechanical issues; Gate B has fix authority for correctness and structural issues, flags architectural concerns. Gate B skips only for pure mechanical changes with no design decisions. If either gate makes fixes, Gate A re-runs before the phase closes. Curator proposes durable learning updates after QA closes clean. See [qa-tester.md](../../agents/qa-tester.md) for the authoritative gate definitions.

## Model Assignment
**Do not specify a `model` parameter in Task tool calls.** Agent definitions in `.cursor/agents/` govern model selection. Passing `model` to the Task tool silently overrides the agent definition and defeats the purpose of per-agent model configuration.

The assembly line principle applies through agent definitions, not Task parameters: executor agents are configured for a fast model (narrow, atomic execution); QA is configured for a capable model (holistic judgment, cross-file reasoning, fix authority). Let those configurations run. Overriding them is a harness break.

## Cursor Agent Type Bug (Critical — Will Recur)
The Task tool intermittently rejects valid `subagent_type` values with a false error: `Invalid enum value. Expected 'generalPurpose' | 'explore' | 'shell' | 'browser-use', received 'the-executor'`. **This error is a lie.** Cursor internally stores all agents as generalPurpose, so the validation message incorrectly lists only base types.

**The fix is always: retry the same call immediately.** The specialized types (`the-executor`, `the-qa-tester`, `the-architect`, `the-curator`, `the-author`, `the-researcher`, `the-visual-qa`) are valid and will succeed on retry. Never fall back to `generalPurpose` — doing so bypasses the agent definition's model selection, behavioral constraints, and self-verification mandates. Every agent that runs as `generalPurpose` instead of its defined type is running without its governance layer.

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

## Two-Mode QA Protocol (Gate A → Gate B)

Every phase closes with two QA passes in sequence. Both are always mandatory unless Gate B skips (pure mechanical changes only). The authoritative gate definitions live in [qa-tester.md](../../agents/qa-tester.md). The language skill governs what "static" means for that stack.

**Gate A** (mechanical correctness + test quality) = Static QA + test anti-pattern audit. Always runs first. Fix authority for compilation, lint, test wiring, and test quality failures.
**Gate B** (holistic judgment) = Qualitative QA. "Is this actually good code?" Fix authority for correctness and structural issues; flags architectural concerns.

### Static QA (Gate A)
Executor self-verification runs static gates before returning — this is not the orchestrator's job. QA runs one terminal static pass after all executor rounds are complete. The orchestrator's permitted action is exactly: run one check, read the headline, stop. Never diagnose individual errors. Never enter the fix loop. The diagnostic loop is QA territory regardless of how small the error looks.

Static cadence varies by language:
- **Rust**: one terminal pass — compiler handles intermediate correctness. See rust-development skill.
- **SvelteKit**: per-phase (`npm run lint && npx svelte-kit sync && npm run check`). No compile-time guarantees for template correctness.
- **Python**: per-phase, with basedpyright scope including the full import graph — not just WFS files. `ruff check` alone is insufficient; the two tools have non-overlapping coverage. **Note**: No python-development skill exists yet. Python QA patterns are currently scattered across this skill and the environment skill. A `python-development` skill encoding per-phase static cadence, basedpyright import-graph scope, and pytest strategy is the correct follow-on — the worst gravity well instances in session history (session 5cd9d6f8, 23 basedpyright errors diagnosed directly by orchestrator) occurred in Python work without this governance layer.

### Qualitative QA (Gate B)
Always the terminal step of any phase, for every language (skip only for pure mechanical changes with no design decisions). The compiler enforces memory safety and types; it does not enforce design. Gate B fills that gap.

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
