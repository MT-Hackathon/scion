---
name: rootstock-mcp
description: "Governs the Rootstock MCP server: stdio transport, dual-mode binary (`rootstock --mcp`), progressive tool unlock pattern, client configuration for Cursor and Claude Desktop, memory injection at session start, and process identity. Use when connecting a client to the MCP server, adding or debugging MCP tools, configuring mcp.json, understanding the progressive unlock pattern, or diagnosing stdio connectivity. DO NOT use for sync/curation lifecycle (see rootstock) or Tauri IPC/command patterns (see tauri-development)."
---

<ANCHORSKILL-ROOTSTOCK-MCP>

# Rootstock MCP Server

## Architecture

The `rootstock` binary operates in two modes, selected at process start:

| Mode | Invocation | Process behavior |
|---|---|---|
| GUI / tray | `rootstock` | Tauri window, system tray, Tauri async runtime |
| MCP server | `rootstock --mcp` | No window, no tray, tokio runtime spun up directly |

The `--mcp` branch in `main.rs` is a clean process fork — Tauri's runtime is not available in this mode, so tokio is initialized directly via `tokio::runtime::Runtime::new()`. The MCP server and the tray are independent OS processes; killing the tray does not terminate active MCP sessions.

**Transport**: stdio JSON-RPC. The client spawns `rootstock --mcp` as a child process and communicates via stdin/stdout. No port is bound — zero network exposure by design.

**Dependency**: `rmcp = "1.1.1"` with `features = ["server", "transport-io"]` (`src-tauri/Cargo.toml`). Upgraded from 0.16 → 1.1.1 during the March 2026 crate decomposition.

**Shared database**: Both modes open the same SQLite DB via `graft_core::db::db_path()`. Memories written through MCP are immediately visible in the GUI, and vice versa.

## Tool Surface

The server implements a progressive unlock pattern. The client starts with 15 always-on tools (gateways + direct-action tools). Calling a gateway fires `ToolListChanged` and makes that category's sub-tools available for the remainder of the session.

**Always-on tools include:**

| Tool | Role |
|---|---|
| `briefing` | Session start context — project state, active memories, git health |
| `check_messages` | Read and clear pending advisory notifications — see [Advisory Design](#advisory-design-check_messages) for what constitutes a valid advisory |
| `get_context` | Recover procedural knowledge from prior sessions |
| `find_capability` | Route a task description to the right tool |
| `search_memory` | FTS search across the curated memory corpus |
| `read_memory` | Progressive disclosure — full detail for a memory by id |
| `write_memory` | Write a decision/learning/correction/calibration to persistent memory |
| `set_profile` | Set project phase/stack/context for session |
| `quality_gate` | Code quality assessment |
| `update_tool_description` | Override tool metadata at runtime |
| `inject_credential` | Vault credential injection for subprocess environments |
| `codebase` | Gateway → unlocks cascade, assess, hotspots, snapshot, delta, etc. |
| `knowledge` | Gateway → unlocks cross_skill_search, integrity_check, etc. |
| `admin` | Gateway → unlocks health, db_info, usage_stats, config tools, etc. |
| `memory` | Gateway → unlocks tag_memory, supersede_memory, link_memory |
| `sync` | Gateway → unlocks sync_status, pull, push, list_projects, etc. |

**Semantic knowledge routing (0.2.15+)**: Knowledge artifacts (skills, rules, agents) are embedded into `knowledge_vectors` in the runtime DB. Tool responses from `assess`, `cascade`, and `curate_check` include "Related skills" footnotes when contextually relevant. `get_context` surfaces relevant skill paths at session start. `find_capability` uses a weighted keyword+vector blend for routing. `overlap_scan` uses BGE-M3 semantic similarity to catch vocabulary-independent overlap.

Full expansion: **66 tools** registered as of 0.2.13 (March 2026). The always-on set (15) plus sub-tools across all gateway categories. Tool count is verified via `admin → db_info` or the tool registry — never hardcode a count in plans or briefs, as it changes with each feature release.

Calling a locked sub-tool returns: `"Category '{cat}' is locked. Call discover('{cat}') first to unlock it."` The client must call the gateway before sub-tools become available.

## Memory Injection

`serverInstructions` is computed once at session start from the SQLite DB:

- Top-8 ranked active memories are prepended under an `## Active Memory` header
- Falls back to just the `CATEGORY_MAP` string if the DB is empty or absent
- Injects persistent memory context into every new MCP session without any tool call

Implementation: `src-tauri/src/mcp/memory.rs` → `compute_server_instructions()`.

## Client Configuration

No config is committed to this repository. Each developer points their client at the installed or locally-built binary.

**Cursor** (`.cursor/mcp.json` in any project root):

```json
{
  "mcpServers": {
    "user-rootstock": {
      "command": "/absolute/path/to/rootstock",
      "args": ["--mcp"]
    }
  }
}
```

**Claude Desktop** (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "rootstock": {
      "command": "/absolute/path/to/rootstock",
      "args": ["--mcp"]
    }
  }
}
```

**During development**: point `command` at the cargo build output:
- Windows: `target\debug\rootstock.exe`
- macOS/Linux: `target/debug/rootstock`

Rebuild with `cargo build -p rootstock` (or `cargo tauri build` for the full app) before expecting changes to take effect. The client process-manages `rootstock --mcp` — restart the client or use its MCP reconnect flow to pick up a new binary.

## Process Identity

When both tray and MCP sessions are running simultaneously, two separate processes appear in Task Manager/Activity Monitor — both named "Rootstock" (from `productName` in `tauri.conf.json`). This is expected. They share the SQLite DB but have independent lifetimes.

MCP server errors surface on stderr: `[rootstock-mcp] server error: ...`

## Source Map

| File | Responsibility |
|---|---|
| `src-tauri/src/main.rs` | Dual-mode entry point; `--mcp` branch |
| `src-tauri/src/mcp/server.rs` | `GraftMcpServer`, `run_stdio_server` |
| `src-tauri/src/mcp/tools.rs` | Tool catalog, progressive unlock, dispatch |
| `src-tauri/src/mcp/memory.rs` | `serverInstructions` computation |

## Advisory Design (check_messages)

`check_messages` is the advisory delivery surface. Advisories must be specific, resource-grounded, and immediately actionable — they report system state the user cannot see. They must NOT narrate patterns the user is already executing.

**The test**: would this advisory cause a different action than the user would take without it? If no, it's noise.

### Valid advisory kinds

| Kind | Example |
|---|---|
| **Error-contextualized** | "A-MEM scan: similarity was 0.73, just below contradiction threshold (0.75). Pair [idm_X, idm_Y] queued for LLM review." |
| **Completion-aware** | "0.2.21 Phase 2 has 3 of 5 signal writers complete. Remaining: staleness (2C), certainty (2F)." |
| **Resource-grounded** | "DB size 340MB, 18K memory_events rows — retention sweep 12 days overdue." |
| **Quality-grounded** | "3 memories with contradiction_count ≥ 3 — review or supersede." |
| **Health-grounded** | "5 memories stuck in enrichment_status='pending' for >2 hours — embedding worker may be stalled." |

### Invalid advisory kinds (explicitly excluded)

- **Behavioral narration**: "You called cascade → assess → get_context three times today." This describes executing the correct workflow, not a problem.
- **Call-count reactive loops**: "4 consecutive tool calls without a memory write." A refactoring wave or large analysis legitimately generates many calls.
- **Workflow suggestions that assume context**: "Consider consulting the Architect." The user knows when to do this.

### Advisory generation

Advisories are computed from `tool_usage` + `memory_events` aggregates, not from LLM reasoning about the session. They are deterministic functions of system state. This keeps them specific, reproducible, and trustworthy.

`memory_events` schema: see [ogham-memory skill](../ogham-memory/SKILL.md#curation-safety-guardrails) — it is owned by the memory lifecycle layer, not the embedding layer.

## Cross-References

- [rootstock](../rootstock/SKILL.md) — sync/curation lifecycle, graft-policy, distribution scripts
- [tauri-development](../tauri-development/SKILL.md) — Tauri command/IPC patterns for GUI mode
- [rust-development](../rust-development/SKILL.md) — Rust conventions for tool handler authoring

</ANCHORSKILL-ROOTSTOCK-MCP>
