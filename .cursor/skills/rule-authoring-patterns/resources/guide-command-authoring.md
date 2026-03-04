# Guide: Command Authoring

Patterns and standards for writing Cursor slash commands (`.cursor/commands/*.md`).

---

## The Core Principle

Commands are agent-facing prompts. The agent reads the command file when `/command` is invoked; the human does not — unless they open the file directly. Write every word for the agent as the reader.

This rules out:
- Usage notes about how to invoke the command ("you can include /X anywhere in your prompt")
- Chain examples written for human readers ("chain it with /build")
- Human-facing framing ("this command helps you...")

## Defaults Over Assumptions

Commands are often invoked in fresh threads with no prior conversation context. Every variable the agent needs must have a concrete default in the command file itself. Invocation context (what the user typed alongside `/X`) supplements defaults — it never replaces them.

Define explicitly:
- **Scope**: what files or diff range to operate on (e.g., `git diff main..HEAD` as the default, with fallback if on main)
- **Fallback**: what to do when no scope is specified in the invocation
- **Override path**: how the user can narrow or redirect scope inline

## Voice and Structure

- Imperative voice addressed to the agent: "Run static analysis first." Not "the agent should run..."
- Front-load critical framing: what the agent is doing and the default scope, before procedural steps
- Inline checklists are appropriate when the command is checklist-driven; keep them inside the command file rather than in a separate resource (commands load in isolation)
- Protocol sections follow scope and framing — the agent needs context before steps

## What to Strip

These patterns appear in commands written as hybrid agent/human docs. Remove them on sight:
- "You can include /X anywhere in your prompt, or use it alone..."
- "This command helps you..."
- Chain examples that illustrate the command for a human reader
- Any section that only makes sense if a human is reading it at invocation time

## Relationship to Rules and Skills

Commands are not rules (they don't activate automatically) and not skills (they're not agent-selected by description). They're pre-packaged prompts the user fires explicitly, often inline within a larger instruction.

This means:
- A command can reference skills and rules by name when it needs the agent to read governing context
- A command should not duplicate what a skill already encodes — reference, don't repeat
- A command can be used alone or composed: `/review` alone works; so does "fix the error handling /review when done"

## Scope

This guide covers `.cursor/commands/*.md` files only. For rule authoring, see the [Rule Authoring Patterns skill](../SKILL.md). For skill authoring, see [skill-authoring-patterns](../../skill-authoring-patterns/SKILL.md).

## Reference: `review.md` as Model

The `review.md` command is the canonical example of these principles applied:
- Opens with default git scope (`git diff main..HEAD`) — self-sufficient in a fresh thread
- Defines override path explicitly
- No human-facing usage notes
- Constitutional checklist inline, not in a separate resource
- References governing skills by name (error-architecture, svelte-ui, accessibility) rather than duplicating their content
