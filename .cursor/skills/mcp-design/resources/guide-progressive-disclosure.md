# Progressive Disclosure

The gateway unlock pattern keeps the initial tool surface small, then expands it when the model shows intent. A gateway tool reveals a category, emits `ToolListChangedNotification`, and makes the subtools available for the rest of the session.

## Design Rules

- Keep the tree one hop deep. Gateway -> tools is reliable enough; gateway -> subgateway -> tools is not.
- Promote lifecycle primitives and daily drivers to always-on when repeated unlocking adds friction without adding safety.
- Do not gate reads while leaving writes free. That creates backwards incentives where the model can mutate state more easily than it can inspect context.
- Keep category names task-legible. The model should know which gateway to choose without knowing internal implementation terms.

## Why One Hop

Mixed-client testing across Cursor, Claude Code, and Claude Desktop showed that two-deep unlock chains are not dependable as of Mar 2026. Some clients surface tool-list changes cleanly once, then degrade or fail to present later expansions consistently.

Design for the client you wish you had and the system will feel elegant. Design for the client you actually have and the system will be dependable.

## When To Promote

Promote a tool out of a category when:

- it is needed in most sessions
- it serves orientation or lifecycle boundaries
- the safety benefit of hiding it is negligible

## Client Matrix

| Surface | ToolListChanged | Sampling | Elicitation | MCPSearch |
|---|---|---|---|---|
| Cursor | Yes | Unknown | Unknown | No |
| Claude Code | Yes | Likely | Unknown | Yes (v2.1.7+) |
| Claude Desktop | Yes | Likely | Unknown | No |
| Generic MCP | Client-specific | Client-specific | Client-specific | No |
