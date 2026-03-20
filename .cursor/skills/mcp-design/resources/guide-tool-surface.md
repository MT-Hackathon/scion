# Tool Surface Design

Group tools by user intent and privilege level, not by code adjacency. A category should answer "what is the model trying to accomplish?" and "what kinds of side effects become possible if this category is visible?"

## Core Rules

- Always-on tools pay rent every session. Reserve them for lifecycle primitives and daily-driver operations that the model needs before it can sensibly do anything else.
- Gated tools are not second-class. They are a deliberate way to keep infrequent, privileged, or high-token capabilities out of the initial action space.
- Category design shapes the action manifold. What the model can see is what it can imagine doing.
- Trust boundaries must survive categorization. Read-only analysis and destructive mutation should not sit side by side just because they touch the same subsystem.

## Promotion Heuristic

Promote a tool to always-on when at least one of these is true:

- It is a lifecycle primitive the model routinely needs at session start or phase boundaries.
- Hiding it behind a gateway creates repeated friction with no meaningful safety benefit.
- The token cost of keeping it visible is lower than the repeated unlock cost and context loss.

Keep a tool gated when:

- It introduces destructive or privilege-escalating actions.
- It is domain-specialized enough that most sessions do not need it.
- Its presence would widen the action space in ways that increase accidental misuse.

## Example

Before unlocking `admin`, the model cannot accidentally call `cleanup_memories`. After unlocking, it can. Category design determines when that possibility enters scope.

That is why categories are safety controls, not mere organization. A weak grouping scheme leaks dangerous affordances into ordinary workflows.
