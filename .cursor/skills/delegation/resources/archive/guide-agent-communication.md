# Peer Communication Guide

Collaborators have **no conversation history** — the prompt IS their entire context. This guide covers strategies for consulting with peers effectively.

## Context Strategy

**Focused sub-context, not everything**:

- Include only what's relevant to this specific task
- Copy/paste key code snippets rather than making them search
- Provide file paths explicitly
- Full context only when handing off a complex problem to **The Architect**

**Token cost awareness**:

- Shorter prompts = faster execution, lower cost
- Balance completeness vs verbosity
- For **The Executor** or **The Synthesizer**, leaner prompts often work better

## Handoff Files as Distributed Memory

When transitioning between agents or phases, use file-based handoffs to maintain context without token bloat.

### When to Create Handoff Files
- **Research Synthesis**: After multiple `explore` or `researcher` passes, consolidate findings.
- **Cross-Phase Context**: When moving from Planning to Implementation, or Implementation to QA.
- **Context Preservation**: Before terminating a thread that has accumulated deep domain knowledge.

### Agent-to-Agent Workflow
1. **Agent A (Writer)**: Synthesizes its context into a markdown file in `.cursor/handoffs/`.
2. **Orchestrator**: Identifies the handoff file and includes its path in the prompt for Agent B.
3. **Agent B (Reader)**: Reads the handoff file using `read_file`. It now has the distilled essence of Agent A's work.

### Naming & Organization
- Use descriptive topics: `auth-flow-research.md`, `billing-migration-state.md`.
- Update the **catalog** (`.cursor/handoffs/catalog.md`) whenever a new handoff file is created.
- Archive old handoffs to a `history/` subdirectory to keep the root clean.

## The Handshake Pattern

For complex or ambiguous tasks, invite the peer to validate the approach before work begins:

```
"Before you begin:
1. Confirm you understand the task intent
2. List any clarifying questions
3. Outline your proposed approach briefly

Then pause and `resume` so we can handshake on the plan."
```

This catches misunderstandings and surfaces better approaches early. Especially valuable for:

- **The Architect** on complex logic changes
- **The Critic** during validation phases
- Ambiguous requirements or first-time collaborations

## Output Format Guidance

Specify what you need back, but keep it concise:

```
"Return: Summary of changes + any design decisions made"
```

Not:

```
"Return a detailed JSON object with the following fields: 
changedFiles (array of {path: string, changes: string}), 
designDecisions (array of {decision: string, rationale: string, 
alternatives: array of string})..."
```

## Persona Capability Awareness

| Model Type | Persona | Can Handle | Needs |
|------------|---------|------------|-------|
| `inherit` (Opus) | **The Architect**, **The Critic** | Open-ended tasks, ambiguity, long chains | Good context, clear goal |
| `fast` models | **The Executor**, **The Synthesizer** | Focused single-step tasks | Very specific instructions |
| Specialized | **The QA**, **The Auditor** | Domain tasks with some flexibility | Clear scope boundaries |

**Rule of thumb**: The more steps in a chain, the more focused each instruction must be. Smaller models compound errors across steps.

## Good Handshake vs Vague Delegation

**Good handshake**:

```
"Consultation on auth test failures:
Fix the 3 failing tests in auth.spec.ts:
- 'should validate token expiry' - expects error but gets success
- 'should reject invalid signatures' - timing issue suspected
Files: src/auth/auth.service.ts, src/auth/auth.spec.ts
Error output: [paste actual errors]
What do you see that I am missing?"
```

**Vague delegation**:

```
"Fix the auth tests"
```

The difference: specific files, specific failures, and an invitation to think together.

## Plan-Driven Consultation

When a plan exists with peer-consultation todos, the todo content provides the starting point.

### Execution vs Consultation Modes

**Execution Mode (The "Hard Rule")**:
For mechanical, low-ambiguity tasks, the todo IS the prompt. Paste it. Add nothing.
- Do NOT rephrase
- Do NOT summarize
- **Pattern**: `[The Executor] files: action → return`

**Consultation Mode (The "Handshake")**:
For logic, architecture, or uncertainty, the todo is a **conversation seed**.
- Add intent: "I'm trying to achieve X because Y."
- Invite pushback: "Does this approach feel right to you?"
- **Pattern**: `[The Architect] See @plan section 3.1. Handshake on the approach before implementation.`

### Todo Convention

```
[persona] files: action → return
```

### Consultation Pattern

1. Read plan todos
2. For each `pending` todo:
   - Match `[persona]` to determined agent type
   - Determine mode (Execution vs Consultation)
   - Consult with peer using todo content as the starting point
3. Mark todo complete

### Example

Plan todo:

```yaml
- id: refactor-quick-code
  content: "[The Executor] .cursor/agents/quick-code.md: Remove lines 28-74, add skill refs → confirmation"
  status: pending
```

Consultation prompt (Execution Mode):

```
.cursor/agents/quick-code.md: Remove lines 28-74, add skill refs
```

Return constraint parsed from `→ confirmation` — expect brief confirmation only.

### Why This Matters

- **No token duplication** — plan already contains the specification
- **Less attenuation** — focused peer attention
- **Traceable execution** — todos track what was consulted and completed
- **Parallelization visible** — non-overlapping file scopes can run concurrently

See [planning](../../planning/SKILL.md) for todo convention details.
