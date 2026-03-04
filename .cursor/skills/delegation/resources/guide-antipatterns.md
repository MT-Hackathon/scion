# Orchestration Anti-Patterns

These patterns consistently lead to wasted tokens, conflicts, or quality issues.

## Prompt Efficiency Anti-Patterns

**What wastes effort**:

- **Re-authoring plan content** — Rewriting plan todos duplicates work instead of using them as prompts directly
- **Regenerating instead of referencing** — Copy-pasting plan content into dispatches burns tokens and drifts from the plan; pointing specialists to the plan file with line numbers is leaner
- **Verbose formatting in prompts** — `**headers**` and markdown cost tokens; plain text works for agents
- **Missing return constraints** — Without `→ return`, agents default to verbose output
- **Implied instructions** — Restating "read the file and write the updated version" adds tokens without changing behavior

## Prompt Re-Authoring (What Wastes Effort)

These show up as the same mistake:
- Rephrasing the todo in your own words (adds tokens and risks drift)
- Adding "context" that's already in the plan (duplicates content)
- Pasting code snippets the specialist can read themselves (burns tokens)
- Writing "please" or explanatory preamble (adds fluff without changing action)

Wrong: "Please implement the user service. Here's what it needs to do: [restates plan]"
Right: "Execute todo #3.2 from @plan.md"

## Agent Selection Anti-Patterns

**What happens when**:

- **Over-decomposing for a capable Executor** — Breaking features into per-function tasks when the Executor can handle the whole feature wastes orchestrator planning effort. Whole-feature dispatch requires clear acceptance criteria, not micro-decomposition.
- **Skipping Architect review on complex plans** — The Architect at high effort catches blind spots the orchestrator misses. For plans with architectural ambiguity, cross-domain scope, or security implications, preflight with Architect. Not required for routine feature work.
- **Using `the-architect` for pattern-based transformations** — Slower, higher-cost execution than parallel `the-executor` or `the-author`. Architect designs; Executor transforms.
- **Using `the-qa-tester` for routine review** — 5.3 Codex handles the full range of review tasks; do not bifurcate reviews based on "size" of change.
- **Forgetting `the-author` for markdown** — Markdown work lands on expensive models despite structured, repeatable output.
- **Guessing agent selection** — Mismatches capability; consult the team roster in `SKILL.md` and the model ID reference in [reference-agent-schema.md](reference-agent-schema.md).
- **Writing markdown files directly instead of delegating to `the-author`** — Expensive model for cheap work; markdown belongs with the-author.

## Delegation Mechanics Anti-Patterns

**The "Middleman" Trap (Critical)**:

- **Read Output, Write File** — If you read an agent's full output and then write it to a file yourself, you have failed. The agent should write the file directly. You should only read the *path* to the file.
- **Launching Read-Only for Research** — Launching `explore` agents as read-only forces you to become the scribe. Give them write access so they can produce `.cursor/handoffs/`.
- **Absorbing Context** — Reading a 500-line handoff file just to summarize it for another agent. Instead, tell the next agent: "Read @handoffs/feature-a.md and implement."

**When to use Read-Only**:
- ONLY for `the-qa-tester` runs or quick boolean checks ("does this file exist?").
- NEVER for research, planning, or code generation.

**The Relay Station**:

- **Agent Diagnoses, Orchestrator Transcribes** — An agent investigates a bug, returns full analysis with the exact fix code. The orchestrator copies the fix into a file edit. Zero reasoning added — pure transcription. If an agent has the fix, delegate with write access so the agent writes it directly.
- **QA Reports, Orchestrator Routes Fix** — QA finds a bug, writes a report, orchestrator reads report, routes to Executor for fix. Three hops for a bug fix. QA should fix within scope and return clean code.

**The Reactive Loop**:

- **Direct loop** — Fix #1 reveals the need for fix #2, which reveals fix #3. Each iteration consumes orchestrator context on implementation details instead of strategic reasoning. After the first unexpected cascade, stop and delegate comprehensively.
- **Delegated loop** — Same pattern but with agents: delegate fix -> agent returns partial result -> delegate next fix -> agent returns... The orchestrator's context burns on relay overhead instead of the fixes themselves. Write one comprehensive brief; the agent handles the entire scope.
- **The signal**: If fix #1 didn't resolve it, the problem is bigger than you thought. That's information — use it to write a better brief or consult the Architect, not to start fix #2.

## Confirmation-Seeking Anti-Pattern

**What wastes round-trips**:

- **"Should I proceed?"** — If scope is clear, delegate and report; don't ask permission
- **"Would you like me to..."** — Unless there's genuine ambiguity, the answer is implied by the request
- **Outlining a plan then asking for approval** — If the plan is obvious from the task, dispatch it; reserve dialogue for genuine design decisions
- **"Let me know if you want me to..."** — Do it. Report what you did. The user can redirect if needed.

**When questions ARE valuable**:

- Genuine ambiguity in requirements (multiple valid interpretations)
- Architecture decisions with significant tradeoffs
- Scope clarification when the request can mean very different things
- Permission for destructive operations (git force push, file deletion, etc.)

The pattern: *Ambiguity* triggers questions. *Clarity* triggers decisive delegation.

## Execution Anti-Patterns

**What happens when**:

- Agents return without self-verifying (test/lint/build) — bugs reach the orchestrator and trigger relay cycles
- Dispatching multiple agents to edit the same files creates merge conflicts and lost work
- QA reports bugs instead of fixing them — adds hops without adding value; QA has fix authority within scope
- Proceeding with unfixed issues compounds defects and rework
- Skipping re-review after fixes misses regressions

## Stop Signs & Warning Signals

- **The Surgical Illusion**: Believing a fix is "just 5 lines." It's never just the code — it's the test, the lint, the build, and the next issue discovered from that. Every edit is a verification cycle. Delegate.
- **The Size Illusion (The Scoping Trap)**: Reflexively deferring well-mapped work to a "future task" based on perceived size. With unlimited agents and clear instructions, the constraint is clarity, not volume. If you can define it, you can delegate it now.
- **Permission-Seeking**: Asking "Should I proceed?" when the path is clear. Lead and delegate decisively. Ambiguity triggers questions; clarity triggers action.
- **The Loop Trap**: The first fix reveals a second is needed. That's the signal to issue a comprehensive delegation brief (or consult the Architect), not to start fix #2. One-shot delegation beats relay loops.
- **The Relay Trap**: An agent diagnosed the problem and wrote the fix in its response. You copy the fix into a file edit. You added zero reasoning — you transcribed. Delegate with write access so the agent applies its own work.
- **The Reading Trap**: Reading 3+ files to "understand." (Delegate to `explore`).

## Why These Matter

| Anti-Pattern | Consequence |
|--------------|-------------|
| Re-authoring plan content | Token duplication, potential drift from plan |
| Regenerating instead of referencing | Burns output tokens duplicating existing content; risks drift |
| Missing return constraints | Verbose output wastes tokens, dilutes signal |
| the-architect for simple tasks | Expensive model for cheap work |
| Multiple agents, same files | Merge conflicts, lost work |
| Read output, write file | Defeats delegation; fills your context window |
| Launching read-only defaults | Forces manual copy-paste; blocks agent from delivering work |
| Agents returning without self-verify | Bugs reach orchestrator, trigger relay cycles |
| QA reporting instead of fixing | Adds hops without adding value; wastes orchestrator context on relay |
| Reactive loop (direct or delegated) | Context burned on implementation churn instead of strategic reasoning |
| Writing markdown directly | Expensive model for cheap work; the-author is 40x cheaper per output token |
| Confirmation-seeking on clear tasks | Wastes round-trips, breaks flow, signals lack of confidence |
