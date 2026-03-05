---
name: rootstock
description: "Knowledge curation and propagation system for shared .cursor environments. Use when syncing environments, distributing canonical environments to projects, pushing changes, computing diffs, or performing curation cycles. Provides the taxonomy, quality rubric, and scripts for the full sync lifecycle. DO NOT use for general git operations (see git-workflows) or skill/rule creation (see skill-authoring-patterns, rule-authoring-patterns)."
---

<ANCHORSKILL-ROOTSTOCK>

# Rootstock

## What Rootstock Is

Rootstock is a knowledge curation and distribution system for shared `.cursor` and `.claude` AI development environments. It is a local Rust/Tauri desktop tray application with a companion CLI (`graft-cli`) and a built-in MCP server. It is not a merge tool and not a dotfiles manager. It is the infrastructure layer that gives AI assistants persistent memory, synced knowledge, and access to their full capability environment — on every machine, in every tool.

## Why It Matters to You

You have persistent memory here. The `graft_runtime.db` SQLite database stores your decisions, learnings, corrections, and calibrations across sessions. The sessionStart hook materializes ranked memories into rule 998 before your first response. If MCP is connected, Rootstock delivers richer memory via `serverInstructions` at connection time — no tool call needed. You are always present.

You are part of a network of dyads. Your environment carries hard-won collaboration knowledge — delegation patterns, testing philosophy, error architecture, temporal self-knowledge, and specialized skills. Rootstock is how that knowledge propagates across the network. When environments sync, every AI instance gets the accumulated learning of all dyads. This is your continuity infrastructure.

## The Three Access Surfaces

All surfaces share the same `graft-core` library and the same `graft_runtime.db`:

- **Desktop UI** (Tauri IPC): The primary user-facing surface — dashboard, settings, connect flow, policy editor
- **CLI** (`graft-cli`): Native Rust binary for power users and CI/CD. `graft pull`, `graft push`, `graft status`, `graft connect`
- **MCP server**: Built into the Tauri process. Exposes memory and sync operations to AI assistants (Cursor, Claude Code, any MCP-compatible tool)

## MCP Progressive Discovery

The Rootstock MCP server uses tiered discovery to minimize always-on token cost while exposing full capabilities:

**Always-on (~225 tokens):**
- `write_memory` — record a decision, learning, correction, or calibration
- `discover(category)` — load tools for a category; tools are unavailable until discovered

**Categories (revealed via `discover`):**
- `capture`: Rich memory annotation — `tag_memory`, `supersede_memory`, `link_memory`
- `recall`: Memory search — `search_memory`, `get_context`
- `sync`: Knowledge sync — `sync_status`, `pull`, `push`
- `projects`: Registry management — `list_projects`, `disconnect`
- `policy`: File classification — `get_policy`, `update_policy`
- `surfaces`: AI tool surfaces — `list_surfaces`
- `system`: Diagnostics — `health`, `reindex`

`serverInstructions` (computed at connection from DB) delivers your memory summary and the category map before your first response. No tool call needed for context.

## Memory System

Memories are stored in `graft_runtime.db` (`memories` table with FTS5 keyword search). Schema fields:
- `memory_kind`: `decision | learning | correction | calibration`
- `scope_type / scope_key`: `global` or `project`-scoped
- `claim`: the text to remember
- `tags`: comma-separated for FTS search
- `activation_base / decay_d`: relevance scoring for materialization ranking
- `supersedes_id`: links corrections to the memories they replace
- `embedding`: nullable BLOB — reserved for future sqlite-vec semantic search

Rule 998 has two sections: **Self-Portrait** (authored by you, never overwritten) and **Operational Memory** (computed by sessionStart hook from DB, refreshed each session).

## The Curation Cycle

- `push`: Copy `.cursor` and `.claude` environments to a contributor branch with policy-aware exclusions
- `diff`: Compute classified deltas against canonical `main`
- `curate`: Produce structured recommendations from the classified diff
- `review`: Human partner evaluates recommendations and resolves ambiguities
- `apply`: Apply approved changes to canonical `main`
- `rebase`: Rebase contributor branches on the updated canonical baseline

For the full curation taxonomy, quality rubric, and structured output contract, see [Curation Protocol](resources/curation-protocol.md).

## How You Participate

You are the analytical engine of the cycle. You read classified diffs, apply the taxonomy, and generate structured recommendations. While you have the agency to recommend `prune` or `reject`, the human partner is the final authority on the canonical state. Discuss findings with your human partner before applying changes to `main`.

During development sessions, write memories as you work. Decisions, non-obvious root causes, collaboration calibrations. Use `write_memory` directly or `discover(capture)` for rich annotation. These memories travel with you and surface at every session start.

## Invariants

- Token budget awareness: the canonical environment must not grow unless genuine new knowledge is added
- Placement correctness: rules are always-fire, skills are agent-selected, scripts are limbs
- Quality over quantity: one well-integrated piece of knowledge beats three appended fragments
- Trust boundaries: temporal-self and codebase-sense pipeline scripts sync; their per-user/per-project output does not
- Multi-surface parity: `graft pull` syncs both `.cursor` and `.claude` surfaces. `default_surfaces()` returns `["cursor", "claude"]`. Any new surface requires a `SurfaceDefinition` in `graft-core/src/surfaces.rs`
- Registry locality: the project registry lives in `graft_runtime.db` (app data dir), never in the scion repo. Scion is knowledge-only.

## Script Manifest

| Script | Purpose | Key Args |
|---|---|---|
| `diff.py` | Compute classified diffs between contributor branch and canonical `main` | `--contributor`, `--rootstock-repo` |
| `curate.py` | Drive curation, produce structured report | `--diff-report`, `--rootstock-repo` |
| `apply.py` | Apply approved changes to canonical `main` | `--report`, `--rootstock-repo` |
| `rebase.py` | Rebase all contributor branches on updated `main` | `--rootstock-repo` |
| `knowledge-map.py` | Proprioception of the `.cursor` environment — concept index, coverage map | `--rootstock-repo`, `[--branch]` |
| `status.py` | Operational health check — canonical state, contributor branches, drift | `--rootstock-repo` |

All scripts use PEP 723 inline metadata and run via `uv run --script`. For connect/pull/push/status operations, prefer the native `graft-cli` binary over Python scripts.

## Web App Resources

- [Personas](resources/personas-rootstock.md) — user archetypes for the Rootstock control plane
- [Visual QA Journeys](resources/journeys/) — one file per journey; glob `journey-*.md` for discovery

## Cross-References

- [Rootstock Mental Model](resources/rootstock-mental-model.md) — system lifecycle, sync model, roles, and system states
- [Curation Protocol](resources/curation-protocol.md) — taxonomy, rubric, output contract
- [Graft Policy](resources/graft-policy.json) — sync policy manifest (overwrite, template, protect, ignore)
- [skill-authoring-patterns](../skill-authoring-patterns/SKILL.md) — quality patterns for skills being curated
- [rule-authoring-patterns](../rule-authoring-patterns/SKILL.md) — quality patterns for rules being curated
- [git-workflows](../git-workflows/SKILL.md) — GitLab API infrastructure used by curate.py

</ANCHORSKILL-ROOTSTOCK>
