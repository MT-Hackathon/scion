# Client Capability Reference

Known capability support for common MCP surfaces. Unknown means unknown; it is not a polite synonym for "probably yes."

| Surface | ToolListChanged | Sampling | Elicitation | MCPSearch | Tool.meta | Progress |
|---|---|---|---|---|---|---|
| Cursor | No (GitHub #2980) | Unknown | Unknown | No | No | No |
| Claude Code | Yes | Likely | Unknown | Yes (v2.1.7+) | No | No |
| Claude Desktop | Yes | Likely | Unknown | No | No | No |
| Generic MCP | Client-specific | Client-specific | Client-specific | No | Client-specific | Client-specific |

## Notes

- **Progressive disclosure** works without `ToolListChanged` via two mechanisms: (1) `list_tools` returns always-on + unlocked tools, reducing noise; (2) gateway response text names the unlocked tools so the AI can call them directly. `mcps/` descriptor files are the AI's permanent access list.
- **Tool.meta**: rmcp 1.1.x. Use `meta.triggers` for task-intent phrases (future retrieval-augmented clients). No current client reads meta — forward-looking infrastructure. Set it; don't depend on it.
- **notify_progress**: rmcp 1.1.x. Check for `progressToken` via `context.meta.get_progress_token()`; skip if absent. Use phase labels with `message` field, not raw percentages. Wired in `snapshot` and `curate_check` handlers.
- **MCP Apps**: Cursor 2.6 supports interactive HTML UIs in agent chat via MCP Apps. Future opportunity: rich tool catalog browser or persistent notification widget. Not in current scope.
- `Likely` means observed ecosystem discussion or partial testing suggests support, but the capability is not locked down enough to treat as universal.
- `Unknown` should drive defensive design, not wishful design.
