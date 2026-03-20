# Agent Brief Template

This template applies to any specialist agent — Executor, Curator, QA, Author, Researcher, or Architect. The structural contract is the same regardless of who receives it: what to build, which mental models to bring in, and how to verify the result. It does not relay the codebase.

**Stop test**: If you have written a fenced code block with a full function body, rewrite it as a behavioral specification. If you have written more than one phrase next to a file name, you have read the file for the agent — delete the extra words. If you have copied quality gate commands instead of referencing `AGENTS.md`, delete and reference.

---

## Brief: [Task Name]

**Task**: [behavioral change in 1–2 sentences; no implementation detail]

**Design reference**: [`path/to/plan.md §Section`](path/to/plan.md) — design decisions are settled; do not re-derive them.

**Starting files** — named, not read; you read them:
- `path/to/file.rs` — [one phrase: role in the change]
- `path/to/component.svelte` — [one phrase]

**Activate these skills before starting**:
- `skill-name` — [one phrase: why it governs this work]

Common combinations for this codebase:

| Work type | Skills to activate |
|---|---|
| Rust backend (graft-core, workflows) | `rust-development` |
| MCP tools / Tauri commands | `rust-development`, `tauri-development` |
| Svelte frontend | `svelte-ui` |
| Knowledge / rules / skills | `skill-authoring-patterns` or `rule-authoring-patterns` |
| Multi-layer (Rust + frontend) | `rust-development`, `svelte-ui`, `tauri-development` |

**Key patterns for this work type**:
- [Pattern that applies — from design or architect consultation]
- [Anti-pattern to avoid — name the failure mode, not the fix]

**Cascade check**: Use `cascade` MCP tool on [file] if available; otherwise `rg` for all callers/importers of [function or module]. Flag anything outside this scope before proceeding.

**Verification**: Run quality gates from `AGENTS.md`. Do not copy commands here — reference the file.

**Not in scope**: [explicit exclusions that prevent scope creep]

---

## For cheaper-model agents (Gemini flash)

Gemini flash agents benefit from more explicit structure when the work involves unfamiliar patterns. Add an **Implementation notes** section with specific constraints the model may not derive from context alone. Do not use this as license to write implementations — use it to name constraints:

```
**Implementation notes** (flash agents only):
- The handler signature pattern is `fn dispatch_X(...) -> ToolFuture { Box::pin(handle_X(...)) }` — follow the existing form exactly.
- Severity routing: warning/error → piggyback; info/notice → check_messages. This is the core invariant.
```

The test: if a senior engineer would derive this from reading one file in the codebase, it belongs in Implementation notes for flash agents only. If it's a principle, it belongs in Key patterns for all agents.
