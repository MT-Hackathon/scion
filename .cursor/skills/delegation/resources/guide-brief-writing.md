# Guide: Writing Agent Briefs

The brief is the contract between the orchestrator and the specialist. It conveys what to build and why, which mental models to bring in, and how to verify the result. It does not relay the codebase. The agent reads source; the orchestrator reads design.

See [`template-executor-brief.md`](template-executor-brief.md) for the working scaffold.

## Field Commentary

**Task**: One or two sentences naming the behavioral change. "Change `update_project_scion_repo` to return `GraftResult<bool>`, and fall through to `insert_project` when it returns false" is complete. A prose description of the implementation is not.

**Design reference**: Point to the plan section. If the design is in a conversation, summarize the decision in one sentence — do not reproduce the conversation.

**Starting files**: This is a reading list, not a summary. The agent finds the function, reads the signature, and implements. If you've written more than a short phrase per file, you've started the agent's job.

**Activate these skills**: Skills are the shared vocabulary. Naming `rust-development` means the executor reads that skill and applies all its governance — error types, result contracts, compilation boundaries, test strategy — without you repeating any of it. This is the highest-leverage line in the brief.

**Key patterns**: This section comes from architect consultation or known failure modes for the work type. It is not derived from reading the codebase. Examples:
- "The notifications table uses soft delivery — mark_delivered, not delete. No rows are destroyed."
- "Return type changes must be traced to all callers — use `cascade` before editing."
- "Do not add a new DB query function when `dequeue_pending_notifications` already exists and covers this case."

**Cascade check**: Point the executor at the codebase-sense tool. This is more reliable than orchestrator pre-reading because the executor sees the actual source, not a relay summary. The telephone game is real.

**Verification**: `AGENTS.md` is the authoritative gate list. Reference it once. If you are specifying commands in the brief, you will eventually diverge from AGENTS.md as the project evolves. Single source of truth.
