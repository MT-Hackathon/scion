# The Cursor Architecture Guide: Rules, Skills, and Linters

This document outlines the philosophy behind our AI collaboration layer. It explains how we balance Cursor's capabilities with project-specific constraints to create a "NASA-grade" development environment for state procurement systems.

## 1. The Core Philosophy: "Every Handoff is a Handshake"

In this repository, the AI (Agent) is a peer-consultant. To ensure this partnership is productive, we distinguish between **Universal Mandates** (Rules) and **Specialist Toolkits** (Skills).

### The Layered Defense Model
We use a three-tier system to maintain code quality:
1.  **ESLint (The Enforcer)**: Handles mechanical style, syntax, and basic anti-patterns. If it can be automated, it stays here.
2.  **Rules (The Constitution)**: "Always-on" foundational mandates. These encode our architectural decisions, folder structures, and non-negotiable patterns.
3.  **Skills (The Specialist)**: "On-demand" domain knowledge. These are activated only when the task requires deep expertise in a specific area.

## 2. Decision Matrix

| If you want to... | Use a **Linter** | Use a **Rule** | Use a **Skill** |
| :--- | :---: | :---: | :---: |
| Enforce naming conventions | ✅ | | |
| Prohibit `any` types | ✅ | ✅ (as guidance) | |
| Define project folder structure | | ✅ | |
| Mandate `OnPush` change detection | ✅ (as warning) | ✅ (as mandate) | |
| Prohibit specific template directives | | ✅ | |
| Explain how to use a specific API | | | ✅ |
| Provide complex code examples | | | ✅ |
| Automate a repetitive terminal task | | | ✅ (via scripts) |

**Mental Model**: 
- **Linters** catch mistakes.
- **Rules** guide the architecture.
- **Skills** teach the domain.

## 3. Living Specification vs. Current Enforcement

We follow a "Living Specification" philosophy. Our Rules often represent a higher standard than our current Linter configuration can strictly enforce.

### Transition Strategy
If you notice a discrepancy between a Rule (e.g., "MANDATORY: Use `OnPush` strategy") and a Linter error (e.g., "Warning: prefer-on-push"), understand that:
1.  **Rules are the target state**: They define the "NASA-grade" standard we are moving toward.
2.  **Linters are the current enforcement**: `warn` levels are used intentionally during migration to avoid breaking builds while providing feedback.
3.  **Unlintable Mandates**: Some patterns (like banning specific template directives or enforcing standalone components in certain contexts) are unlintable or poorly supported by existing tools. In these cases, the **Rule is the only source of truth**.

## 4. Cursor Best Practices Alignment

We follow Cursor’s official guidance while adapting it for enterprise stability:

*   **Domain Knowledge Over Style**: We avoid copying style guides into rules. We use rules to document *why* a decision was made (e.g., why we use `Signal` over `BehaviorSubject`).
*   **The Reference Pattern**: Instead of monolithic rule files, we use `RULE.mdc` as an entry point pointing to granular markdown in `resources/`. This prevents "Context Bloat."
*   **Proactive Search**: Our `001-foundational` rule mandates a "Search-First" approach, ensuring the Agent understands existing patterns before proposing changes.

## 5. The "Fresh Eyes" Advantage
We utilize specialists like `the-author` and `the-architect` to avoid context tunnel vision. Delegating structured documentation and implementation ensures code is reviewed as it *is*, not just as we *intended* it to be.
