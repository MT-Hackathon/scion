# Rule Authoring Philosophy

Core principles for designing effective rules and skills.

## The Specificity Principle

Rules encode YOUR approach, not generic best practices.

**Generic (weak):**

- "Use descriptive variable names"
- "Follow testing best practices"
- "Design accessible UIs"

**Specific (strong):**

- "Entity names use plural nouns; component names use CapWords" (project convention)
- "Integration tests require fixture isolation via pytest marks" (project approach)
- "Forms use Formsnap + Zod; validation errors display inline above submit" (project stack)

**Every rule should answer:** "How does THIS PROJECT do this?" — not "How should code generally be written?"

## The Workspace Memory Pattern

Rules are operational memory — how you work, not how one should work.

**This means:**

- Rules encode your approach (not all possible approaches)
- Rules evolve as the project evolves
- Rules are composable (multiple rules activate together seamlessly)

When two rules conflict, it signals your approach is diverging — time to consolidate or clarify boundaries.

## The Composability Principle

The best rules are narrow but ecosystem-aware.

**Example:** When writing backend code, these rules compose automatically:

- 100-constitution-core (code principles)
- 101-constitution-testing (testing patterns)
- 102-ecs-architecture (ECS specifics)

No manual coordination needed. They work together seamlessly.

**Design for:** Single responsibility + ecosystem awareness

## How Patterns Are Discovered

Rules emerge from the feedback loop:

1. **Implicit:** You notice you keep doing X across conversations
2. **Codified:** Extract into a rule with real examples from your projects
3. **Distributed:** Rule is used across conversations, tested in context
4. **Evolved:** Refine based on edge cases discovered

This cycle is continuous. Rules aren't final — they're living documentation of how you've learned to work.
