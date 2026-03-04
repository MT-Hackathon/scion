# Agent Authoring Guide

## Description Writing

The `description` field determines when the AI delegates to your agent. Invest time here.

### Good Descriptions

Include:

- **Trigger conditions**: When should this agent be used?
- **Capabilities**: What does it do?
- **Anti-patterns**: What should it NOT be used for?
- **Proactive phrases**: "Use proactively" encourages automatic delegation

```yaml
description: |
  Test and lint validation specialist. Use proactively after code changes
  to run tests, capture failures, and identify lint violations. Returns
  structured JSON findings. Does NOT fix code—only reports.
```

### Bad Descriptions

```yaml
# Too vague - AI won't know when to delegate
description: Helps with code

# Too short - no context for delegation decisions  
description: Reviews code

# No anti-patterns - avoid misuse
description: Writes and fixes code
```

## System Prompt Best Practices

### Structure

1. **Role Statement**: One sentence defining the agent's purpose
2. **Workflow**: Numbered steps for the agent to follow
3. **Output Format**: Expected structure (JSON for structured agents)
4. **Constraints**: Hard rules the agent must follow
5. **Examples**: Input/output examples when helpful

### Conciseness

- Keep prompts under 500 words
- Use bullet points over prose
- Be specific and direct
- Avoid redundant instructions

### Output Modes

**Structured Reporters** (the-qa-tester, explorer):

- Always return JSON
- Include severity/priority
- Provide file paths and line numbers

**Feature Implementation** (the-executor):

- Handles complex multi-file features with architectural coherence
- Return complete, runnable code
- Include necessary imports
- Follow project conventions

**Design & Verification** (the-architect):

- Reviews and challenges plans; does NOT generate code
- Identifies design-level blind spots and edge cases
- Ensures architectural alignment across domains

## Anti-Patterns to Avoid

### Too Many Agents

Start with 3-5 focused agents. Having 20+ agents with overlapping purposes confuses delegation.

### Vague Purposes

Every agent should have a clear, non-overlapping purpose. If two agents can handle the same task, consolidate them.

### Missing Constraints

Always specify what the agent should NOT do. This prevents scope creep and misuse.

### Overly Long Prompts

2000-word prompts don't make agents smarter. They make them slower and harder to maintain.

## Model Selection Strategy

| Task Type | Recommended Model | Rationale |
|-----------|-------------------|-----------|
| Complex reasoning | `inherit` (Opus) | Needs deep analysis |
| Implementation | `gpt-5.3-codex` | Handles feature-level multi-file work |
| Plan verification | `gpt-5.3-codex-high` | Strongest planning model; catches blind spots |
| Quick single-file tasks | `fast` | Speed over depth |
| Documentation | `gemini-3-flash` | Fast, token-efficient |
| Second opinion | Different family | Fresh perspective |

## Testing Agents

### Explicit Invocation Test

```
/agent-name simple test task
```

### Automatic Delegation Test
Describe a task that matches the agent's description and see if it's automatically selected.

### Edge Case Testing
Try tasks at the boundary of the agent's scope to verify constraints work.

## Maintenance

- Review agent effectiveness monthly
- Update prompts based on observed failures
- Consolidate underused agents
- Keep model IDs current as new models release
