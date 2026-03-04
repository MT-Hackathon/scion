# Rules in Context: Comparison with Skills and Agents

Cursor supports three distinct types of AI guidance. Understanding the boundaries between them ensures rules remain lean and focused on architectural mandates.

| Type | Format | Activation | Ideal For... |
| :--- | :--- | :--- | :--- |
| **Rule** | `.mdc` file | **Automatic**: Always-on or Glob-based | Constraints, mandates, and structural patterns. |
| **Skill** | Folder structure | **Intelligent**: Description-based keywords | Specialized domain knowledge and utility scripts. |
| **Agent** | Persona file | **Delegated**: Explicit selection | Specialized workflows and isolated context windows. |

## Why Use a Rule?

Rules are the most powerful form of guidance because they do not rely on keyword matching to activate. They are part of the "system prompt" for any matching file.

- **Mandatory Enforcement**: If a pattern must *never* be violated (e.g., NASA Power of 10), use a Rule.
- **Universal Context**: If information is needed in every single turn (e.g., Project Foundational Rules), use an always-on Rule.
- **Language/Framework Guardrails**: If a pattern applies specifically to a file type (e.g., Angular component structure), use a Rule with a glob.

## Rules vs. Other Types

### Rules vs. Skills
- **Skills** teach the AI *how* to do something when asked (e.g., "How do I use this internal API?").
- **Rules** tell the AI what it *must* or *must not* do while working (e.g., "Do not use `any` in this project").
- **Use a Rule** when you want to enforce a standard. **Use a Skill** when you want to provide a library of knowledge or complex scripts.

### Rules vs. Agents
- **Agents** are specialized personas for specific tasks (e.g., "The Architect" or "The QA").
- **Rules** govern the behavior of *all* agents and the primary AI assistant.
- **Use a Rule** for cross-cutting mandates that all agents should follow. **Use an Agent** when a task requires a specific focus or a different model.

## Selection Matrix

| If you want to... | Use a **Rule** | Use a **Skill** | Use an **Agent** |
| :--- | :---: | :---: | :---: |
| Enforce architectural constraints | ✅ | | |
| Define file-specific standards (globs) | ✅ | | |
| Provide reusable domain guides | | ✅ | |
| Automate repetitive terminal workflows | | ✅ | |
| Create a specialist for code review | | | ✅ |
| Handle complex, multi-file migrations | | | ✅ |

## Reconciling with Other Patterns

- For skill-specific patterns, see [skill-authoring-patterns](../SKILL.md).
- For agent and delegation patterns, see [delegation](../../delegation/SKILL.md).
- For procedural creation of rules, see [create-rule](@/home/cmb115/.cursor/skills-cursor/create-rule/SKILL.md).
