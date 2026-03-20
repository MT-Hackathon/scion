# Tool Composition

Common Rootstock MCP sequences and the situations they serve.

## Pattern 1 - Pre-Change Briefing

```text
`codebase` (Entry Point) -> `cascade(file)` -> [read files] -> implement -> `check_messages`
```

Use when planning or validating a code change that may have blast-radius risk.

## Pattern 2 - Curation Session

```text
`workshop` (Entry Point) -> `curate_check`
```

Use the quick path for a bounded audit.

```text
`workshop` (Entry Point) -> `curate_health` + `integrity_check` + `staleness_scan`
```

Use the thorough path when you need separate signals.

Then:

```text
cross_skill_search(concept) -> write_memory(kind="decision", content="pruned X because Y")
```

Use this when the audit turns into a real curation decision that should persist.

## Pattern 3 - Sync Cycle

```text
`sync` (Entry Point) -> `sync_status` -> [review drift] -> `pull` OR `push` -> `write_memory(kind="decision", ...)`
```

Use when checking project drift and recording why a sync action was taken.

## Pattern 4 - Multi-Project Sync Review

```text
`projects` (Entry Point) -> `list_projects`
`sync` (Entry Point) -> `sync_status`
```

Use when you need both the global project roster and per-project drift details.

## Pattern 5 - End Of Session

```text
check_messages -> write_memory(kind=...) -> [update 998 rule if narrative changed]
```

Use at session close so advisory signals are drained and non-obvious learning is preserved.
