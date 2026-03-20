# Description Design

Descriptions are retrieval features, not documentation. MCP clients and model search layers match tools by task language, so the description must act like search bait for real intent.

## The Pattern

Use one sentence with this shape:

`when -> outcome -> boundary`

- `when`: the task trigger or situation
- `outcome`: what capability becomes available
- `boundary`: what this tool or category is not for

## Weak vs Strong

- Weak: `capture — memory management: tag, supersede, link`
- Strong: `memory — When working with past decisions or session context, unlock search, retrieval, tagging, and memory evolution tools. DO NOT use for memory curation/deletion (see admin).`

- Weak: `codebase — codebase intelligence tools`
- Strong: `codebase — When planning a code change or tracing blast radius, unlock dependency analysis, test mapping, hotspot ranking, and refactor references.`

The weak forms describe nouns. The strong forms describe tasks.

## Why This Matters

Claude Code's MCPSearch indexes tool descriptions, so a good description directly affects whether the model even discovers the right capability. Even on clients without explicit MCPSearch, models still reason from tool names plus description text, which makes the description a retrieval surface everywhere.

## Property Descriptions

Schema property descriptions should answer:

- what the parameter means
- how the server interprets it
- what common misuse to avoid

Use examples only on high-ambiguity properties. Property-level examples improve invocation accuracy without bloating always-on descriptions.

## Triggers Metadata

If your registry supports metadata, add a `triggers` field with likely task phrases such as `trace blast radius`, `find stale skills`, or `review sync drift`. This supplements the description with alternate user language without making the visible description unreadable.
