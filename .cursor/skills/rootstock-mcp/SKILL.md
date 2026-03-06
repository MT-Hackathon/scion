---
name: rootstock-mcp
description: "Governs the Rootstock MCP server: stdio transport, dual-mode binary (`rootstock --mcp`), progressive tool unlock pattern, client configuration for Cursor and Claude Desktop, memory injection at session start, and process identity. Use when connecting a client to the MCP server, adding or debugging MCP tools, configuring mcp.json, understanding why tool count changes from 8 to 23, or diagnosing stdio connectivity. DO NOT use for sync/curation lifecycle (see rootstock) or Tauri IPC/command patterns (see tauri-development)."
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

**Dependency**: `rmcp = "0.16"` with `features = ["server", "transport-io"]` (`src-tauri/Cargo.toml`).

**Shared database**: Both modes open the same SQLite DB via `graft_core::db::db_path()`. Memories written through MCP are immediately visible in the GUI, and vice versa.

## Tool Surface

The server implements a progressive unlock pattern. The client starts with 8 gateway tools. Calling a gateway fires `ToolListChanged` and makes that category's sub-tools available for the remainder of the session.

**Always-on (8 tools):**

| Tool | Role |
|---|---|
| `write_memory` | Write a decision/learning/correction/calibration to persistent memory (performs work directly) |
| `capture` | Gateway → unlocks `tag_memory`, `supersede_memory`, `link_memory` |
| `recall` | Gateway → unlocks `search_memory`, `get_context` |
| `sync` | Gateway → unlocks `sync_status`, `pull`, `push` |
| `projects` | Gateway → unlocks `list_projects`, `disconnect` |
| `policy` | Gateway → unlocks `get_policy`, `update_policy` |
| `surfaces` | Gateway → unlocks `list_surfaces` |
| `system` | Gateway → unlocks `health`, `reindex` |

Full expansion: **23 tools** (8 always-on + 15 sub-tools across 7 categories). `write_memory` is the only always-on tool that is not a gateway.

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

## Cross-References

- [rootstock](../rootstock/SKILL.md) — sync/curation lifecycle, graft-policy, distribution scripts
- [tauri-development](../tauri-development/SKILL.md) — Tauri command/IPC patterns for GUI mode
- [rust-development](../rust-development/SKILL.md) — Rust conventions for tool handler authoring

</ANCHORSKILL-ROOTSTOCK-MCP>
