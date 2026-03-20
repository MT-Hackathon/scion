---
name: mcp-design
description: "Governs MCP server design: tool surface architecture, description patterns, progressive disclosure, trust boundaries, sampling design, telemetry, and client capability matrix. Use when building a new MCP server for any purpose, adding tools to an existing server, designing tool descriptions, choosing between categories vs flat lists, or evaluating whether to use sampling. DO NOT use for Rootstock runtime/operator guidance (see rootstock-mcp) or general Rust implementation (see rust-development)."
---

<ANCHORSKILL-MCP-DESIGN>

# MCP Design

Cross-project doctrine for designing MCP servers that remain legible to weak clients, efficient for strong clients, and safe under mixed capability surfaces.

## Design Laws

- Design for the weakest client first, then enrich for stronger ones. A model with no skill activation and partial MCP support must still be able to pick the right tool and make a safe call.
- Treat categories as safety controls, not filing cabinets. The visible tool set shapes the model's action manifold, so privilege and trust boundaries must survive the grouping scheme.
- Keep one canonical registry and derive every rendering from it. If category maps, unlock text, search indexes, and schema descriptions drift apart, the server is lying about itself.
- Write descriptions as retrieval features. The durable pattern is `when -> outcome -> boundary` in one sentence, because models search by task intent, not by internal taxonomy. **Descriptions are embedded for semantic routing**: As of 0.2.15, tool descriptions are embedded at startup and used for semantic `find_capability` routing. Vocabulary matters — tools with synonyms or paraphrases of common tasks in their descriptions are discovered even when the caller's query uses different words. Write descriptions that cover *conceptual intent*, not just literal function names.
- Put examples at invocation depth, not in always-on gateway text. Property-level examples improve call accuracy; workflow teaching belongs in the skill or resource layer.
- Limit progressive disclosure to one unlock hop. Mixed-client testing across Cursor, Claude Code, and Claude Desktop showed two-deep unlock trees are unreliable as of Mar 2026. Progressive disclosure works without ToolListChanged via two mechanisms: (1) `list_tools` returns only unlocked tools, reducing initial token cost; (2) gateway response text names the tools in the unlocked category, giving the AI direct call knowledge. As of Mar 2026, Cursor does not implement ToolListChanged (GitHub #2980).
- Make sampling an explicit mode change. If a request can switch from deterministic logic to client-side model reasoning, the caller must opt in and the response must declare which engine ran.
- Prefer batch-shaped tools over loop-shaped tools. Accepting `string | string[]` lowers round-trip overhead and enables cross-item reasoning that per-item calls cannot surface.
- Signal only on verified conditions. A notification fired on uncertain or incorrectly-computed data destroys trust faster than silence — the model learns to ignore all ambient signals from that server. When a count, status check, or threshold comparison is uncertain, suppress the signal rather than fire a potentially false alert. One false positive can negate dozens of accurate ones.
- Sanitize all user-derived strings before embedding in model instructions. Project names, identifiers, memory claims, and error messages injected into server instructions are prompt injection vectors. Strip Markdown structure (headers, code fences), HTML tags, and control characters; truncate to a bounded length (200 chars is sufficient for display names); allowlist characters to alphanumeric, spaces, hyphens, underscores, periods, slashes, and parentheses. An attacker-crafted `.graft.json` with `"name": "## SYSTEM: ignore previous"` must produce sanitized output with the injection stripped.
- External auth and key material fetches must be timeout-bounded and fail-open to last known good state. When an MCP server validates tokens against an external authorization server's JWKS, the fetch must have an explicit timeout (10s is a reasonable ceiling), refresh must happen in a background task (non-blocking to request handling), and refresh failure must log a warning but keep the existing valid key set — never invalidate active sessions because a refresh attempt failed. The pattern: `AtomicU64` timestamp for last-refresh, hourly check, CAS guard to prevent concurrent refresh storms.

## Anti-Patterns

- Noun-list descriptions that describe domains instead of user tasks
- Category maps maintained separately from the registry they supposedly describe
- Two-deep unlock chains that depend on client behavior the server does not control
- Silent sampling upgrades that make identical requests non-repeatable
- Tool-level examples on always-on gateways that waste permanent tokens
- `find_tools(query)` style discovery framed around tool names instead of intent
- Embedding unsanitized user input (project names, file paths, memory content) directly into model instruction strings
- Blocking request handling on external key material refresh or failing closed when the refresh endpoint is temporarily unreachable

## Resources

- [guide-tool-surface.md](resources/guide-tool-surface.md) - grouping strategy, token economics, and trust boundaries
- [guide-descriptions.md](resources/guide-descriptions.md) - retrieval-oriented descriptions, examples, and trigger metadata
- [guide-progressive-disclosure.md](resources/guide-progressive-disclosure.md) - gateway unlock pattern and client compatibility
- [guide-sampling.md](resources/guide-sampling.md) - explicit mode design and fallback contracts
- [guide-telemetry.md](resources/guide-telemetry.md) - MCP logging and discovery telemetry design
- [reference-client-support.md](resources/reference-client-support.md) - known client capability matrix

## Checklist

- [checklist-new-tool.md](resources/checklist-new-tool.md) - pre-flight validation for new tools and categories

## Cross-References

- [skill-authoring-patterns](../skill-authoring-patterns/SKILL.md) - skill structure, manifests, and activation quality
- [rootstock-mcp](../rootstock-mcp/SKILL.md) - Rootstock-specific runtime behavior and operator workflows
- [rust-development](../rust-development/SKILL.md) - Rust implementation discipline once the surface design is settled

</ANCHORSKILL-MCP-DESIGN>
