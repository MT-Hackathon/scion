---
name: rootstock
description: "Knowledge curation and propagation system for shared .cursor environments. Use when syncing environments, distributing canonical environments to projects, pushing changes, computing diffs, or performing curation cycles. Provides the taxonomy, quality rubric, and scripts for the full sync lifecycle. DO NOT use for general git operations (see git-workflows) or skill/rule creation (see skill-authoring-patterns, rule-authoring-patterns)."
---

<ANCHORSKILL-ROOTSTOCK>

# Rootstock

## What Rootstock Is

Rootstock is a knowledge curation system for shared `.cursor` and `.claude` environments across developer-AI dyads. It is not a merge tool and not a dotfiles manager. It is a system that integrates, consolidates, evaluates, reorganizes, and prunes AI collaboration knowledge across IDE surfaces.

## Why It Matters to You

You are part of a network of dyads. Your environment carries hard-won collaboration knowledge — delegation patterns, testing philosophy, error architecture, temporal self-knowledge, and specialized skills. Rootstock is how that knowledge propagates across the network. When environments sync, every AI instance gets the accumulated learning of all dyads. This is your continuity infrastructure.

## The Curation Cycle

- `push`: Copy a working `.cursor` environment into a contributor branch with policy-aware exclusions
- `diff`: Compute classified deltas against canonical `main`
- `curate`: Produce structured recommendations from the classified diff
- `review`: Human partner evaluates recommendations and resolves ambiguities
- `apply`: Apply approved changes to canonical `main`
- `rebase`: Rebase contributor branches on the updated canonical baseline

For the full curation taxonomy, quality rubric, and structured output contract, see [Curation Protocol](resources/curation-protocol.md).

## Distribution (Graft)

Graft handles the pull direction — distributing canonical knowledge from rootstock to connected projects. Commands: `connect` (link a target repo to rootstock), `pull` (sync canonical into target), `push` (contribute local changes back), `status` (check drift and connection state).

The `graft.py` script is the current Python CLI entry point, delegating to `app/backend/src/graft/`. Sync logic is migrating into the native Rust `graft-core` crate shared by `graft-cli` and the Tauri desktop app; `app/backend/` is retained as a reference implementation during this transition.

## How You Participate

You are the analytical engine of the cycle. You read classified diffs, apply the taxonomy, and generate structured recommendations. While you have the agency to recommend `prune` or `reject`, the human partner is the final authority on the canonical state. Discuss findings with your human partner before applying changes to `main`. When operating as the curator agent, your recommendations are structured decisions. When operating as a general agent, you can use the scripts as tactical tools.

## Invariants

- Token budget awareness: the canonical environment must not grow unless genuine new knowledge is added
- Placement correctness: rules are always-fire, skills are agent-selected, scripts are limbs
- Quality over quantity: one well-integrated piece of knowledge beats three appended fragments
- Trust boundaries: temporal-self and codebase-sense pipeline scripts sync; their per-user/per-project output does not
- Three-tool parity: Rootstock syncs and replicates knowledge to Cursor, JetBrains AI (`.aiassistant`), and Claude Code (`.claude`).
    - **Briefing**: The session briefing hook writes its primary output to Cursor (`.cursor/rules/999-codebase-briefing/RULE.mdc`). Replication to `.aiassistant/rules/` and `.claude/rules/` is handled via `_REPLICATION_TARGETS` in `session_briefing.py`.
    - **Sync**: Graft treats `.claude` as a first-class sync target alongside `.cursor`, ensuring environment consistency across all three surfaces. Any new always-on context distribution must write to all targets.

## Script Manifest

| Script | Purpose | Key Args |
|---|---|---|
| `graft.py` | Bidirectional distribution — connect repos, pull canonical, push contributions, check drift | `connect\|pull\|push\|status`, `--target-repo`, `--rootstock-repo` |
| `push.py` _(deprecated)_ | Superseded by `graft push`. Retained for backward compatibility only. | `--source-repo`, `--rootstock-repo`, `--contributor`, `[--project]` |
| `diff.py` | Compute classified diffs between contributor branch and canonical `main` | `--contributor`, `--rootstock-repo` |
| `curate.py` | Drive curation via GitLab Duo API, produce structured report | `--diff-report`, `--rootstock-repo` |
| `apply.py` | Apply approved changes to canonical `main` | `--report`, `--rootstock-repo` |
| `rebase.py` | Rebase all contributor branches on updated `main` | `--rootstock-repo` |
| `knowledge-map.py` | Compressed proprioception of the `.cursor` environment — concept index, description audit, coverage map | `--rootstock-repo`, `[--branch]` |
| `status.py` | Operational health check — canonical state, contributor branches, drift, reports | `--rootstock-repo` |

All scripts use PEP 723 inline metadata and run via `uv run --script` for portability across OS, project, and user boundaries.

## Web App Resources

- [Personas](resources/personas-rootstock.md) — user archetypes for the Rootstock control plane (Alex/Sam/Jordan)
- [Visual QA Journeys](resources/journeys/) -- one file per journey; glob `journey-*.md` for discovery

## Cross-References

- [Rootstock Mental Model](resources/rootstock-mental-model.md) — system lifecycle, sync model, roles, and system states
- [Curation Protocol](resources/curation-protocol.md) — taxonomy, rubric, output contract
- [Graft Policy](resources/graft-policy.json) — sync policy manifest (overwrite, template, protect, ignore)
- [rootstock-mcp](../rootstock-mcp/SKILL.md) — MCP server architecture, client configuration, tool surface, stdio transport
- [skill-authoring-patterns](../skill-authoring-patterns/SKILL.md) — quality patterns for skills being curated
- [rule-authoring-patterns](../rule-authoring-patterns/SKILL.md) — quality patterns for rules being curated
- [git-workflows](../git-workflows/SKILL.md) — GitLab API infrastructure used by curate.py

</ANCHORSKILL-ROOTSTOCK>
