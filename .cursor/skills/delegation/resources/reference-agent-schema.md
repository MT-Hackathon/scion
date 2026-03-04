# Agent Schema Reference

## Frontmatter Fields

| Field | Required | Type | Default | Description |
|-------|----------|------|---------|-------------|
| `name` | No | string | filename | Unique identifier (lowercase, hyphens only) |
| `description` | No | string | - | When to delegate to this agent. Critical for automatic delegation. |
| `model` | No | string | `inherit` | Model to use: `fast`, `inherit`, or specific model ID |
| `readonly` | No | boolean | `false` | If true, agent cannot write/modify files |
| `is_background` | No | boolean | `false` | If true, runs without blocking parent agent |

## Model ID Reference

Cursor's UI displays human-friendly names, but YAML uses hyphenated format:

| UI Display | YAML Model ID | Use Case |
|------------|---------------|----------|
| (parent model) | `inherit` | Use parent agent's model (default) |
| (fast model) | `fast` | Quick, less capable model |
| Claude Opus 4.5 | `claude-opus-4-5-20251101` | Complex reasoning, architecture |
| gpt-5.3 Codex | `gpt-5.3-codex` | Implementation, QA, visual audit |
| gpt-5.3 Codex High | `gpt-5.3-codex-high` | Architecture, plan verification, deep reasoning |
| Gemini 3 Flash | `gemini-3-flash` | Fast documentation generation |

**Note:** GPT-5.3 Codex is the default engine for technical specialists. Use High Effort for plans, complex logic, or plan verification.

## File Format

```markdown
---
name: agent-name
description: |
  When to use this agent. Include trigger phrases.
  Describe what it does and what it does NOT do.
model: inherit
readonly: false
is_background: false
---

# Agent Title

System prompt content here. This becomes the agent's instructions.

## Sections as needed

Structure the prompt for clarity.
```

## File Locations

| Location | Scope | Priority |
|----------|-------|----------|
| `.cursor/agents/` | Current project | Higher (wins on name conflict) |
| `~/.cursor/agents/` | All user projects | Lower |

## Invocation Methods

### Automatic Delegation
Agent reads descriptions and delegates based on task match. Include phrases like "use proactively" to encourage automatic use.

### Explicit Invocation

```
/agent-name do the task
```

Or natural language:

```
Use the agent-name subagent to do the task
```

## Naming Convention

- Use lowercase with hyphens: `the-qa-tester`, `the-executor`
- Be descriptive but concise
- Avoid generic names like `helper` or `assistant`
