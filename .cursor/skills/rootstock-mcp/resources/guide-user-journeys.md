# User Journeys

Rootstock MCP is strongest when the work needs computed analysis, ranked context, or stateful project operations. It is not the fastest path for every lookup.

## Session Start

`serverInstructions` injects active memories, system alerts, and the category map automatically. No tool calls are needed for basic orientation.

- `get_context()` is always-on and returns ranked memories for the current session
- `check_messages()` is always-on and drains the advisory queue

## Code Change Workflow

1. `codebase` (Entry Point) -> `cascade(file)` for blast-radius analysis
2. Read affected files and implement the change
3. `check_messages()` before declaring the phase complete

## Skill Curation Workflow

1. `workshop` (Entry Point) -> `curate_check` for a bounded combined audit
2. Or run `curate_health`, `integrity_check`, and `staleness_scan` individually for a fuller audit
3. Use `cross_skill_search(query)` to find where a concept is already documented

## Memory Write At End Of Session

Use `write_memory()` directly. It should be frictionless.

Kinds:

- `decision` - a choice made with rationale
- `learning` - a technical or procedural discovery
- `correction` - supersedes previous incorrect understanding
- `calibration` - an observation about collaboration patterns or interaction quality

Tag memories with file paths or module names when they relate to specific code. That makes future cascade lookups more useful.

## Memory Retrieval

Use `get_context()` first because it returns the top-ranked active memories. If the needed item is not there, use `search_memory(query)` with concrete keywords. If it still is not found, the synthesized narrative in rule `998` is the fallback memory layer.

## Sync Workflow

1. `sync` (Entry Point) -> `sync_status` to inspect drift
2. `push(project_id)` to publish to the contributor branch
3. Or `pull(project_id)` to bring changes from scion

## Correction Recording

1. `write_memory(kind="correction", content="...", tags="...")` immediately
2. Or if you need to revise an older memory, use the `memory` (Entry Point) to unlock `supersede_memory(old_id, new_content)`

## What MCP Does Not Replace

- Quick text search: use grep/ripgrep directly for a single-keyword lookup
- Reading skill files: use the normal file read path when you already know the file
- Simple project status: sometimes reading `.graft.json` directly is faster than unlocking `projects`

MCP earns its keep when the value comes from computed analysis: cascade risk scoring, churn-weighted hotspots, sync drift computation, or structured curation reports.
