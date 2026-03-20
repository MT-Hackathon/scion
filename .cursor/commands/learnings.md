# learnings

Scan this thread for anything worth integrating — but lead with the question of what to refine or prune, not what to add. Bad information in the environment actively misleads every future session. Missing good information is just a gap. The asymmetry matters.

Before proposing any addition, check whether it contradicts, extends, or supersedes something already there. If it supersedes, prune the old content. If it extends, integrate rather than append. New standalone artifacts are the last resort, not the default.

## Where Learnings Live

Learnings have three homes, not one. Choose based on scope:

| Scope | Destination | Examples |
|-------|-------------|----------|
| **Portable engineering** (any project) | Portable rules (000-199) or portable skills | Rust idioms, delegation patterns, Cursor operational gotchas |
| **Project-specific** (Rootstock only) | Project rules (200+) or project skills | MCP server architecture, Tauri IPC patterns, sync model |
| **Experiential / session-scoped** | Memories (write_memory) | Failure modes, calibration, collaboration moments, decisions |

Rules and skills are authoritative — they fire deterministically. Memories are contextual — they surface via ranking and may not appear. If something must change behavior every session, it belongs in a rule or skill. If it's institutional knowledge that enriches context, it belongs in a memory.

## Process

1. **Read the governing skills first**: Read skill-authoring-patterns and rule-authoring-patterns before writing to any skill or rule. They encode the quality rubric, placement logic, and token budget constraints.

2. **Classify each learning**: Is it portable engineering, project-specific, or experiential? This determines the destination.

3. **Check for overlap**: Search existing rules and skills for the concept before adding. Use `rg` or explore agents. Integration > accumulation (Invariant 3).

4. **Write or update the artifact**:
   - For rules/skills: use the authoring skill's patterns (folder structure, resource naming, progressive disclosure).
   - For memories: use the ogham-memory skill's write rubric (7 kinds, "would I carve this?" gate).

5. **Curate**: Use the Curator to evaluate changes against the quality rubric — token efficiency, placement correctness, overlap detection. Use one Curator to write and another to review. Then review it yourself: does it speak to you? If it reads like committee output, it isn't done yet.
