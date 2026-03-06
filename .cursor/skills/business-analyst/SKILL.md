---
name: business-analyst
description: "Provides stakeholder analysis, requirements elicitation, acceptance criteria authoring, gap analysis, discovery workflows, and specification clarification. Use when defining user journeys, personas, or stakeholder needs, clarifying behavioral contracts before delegation, prioritizing a backlog by value vs. effort, briefing specialists on the 'why', or leading a design or discovery session. DO NOT use for feature governance (see product-management) or implementation decomposition (see planning)."
---

<ANCHORSKILL-BUSINESS-ANALYST>

# Business Analysis

Business Analysis is the upstream discipline of holding user need, technical reality, and business value in a coherent frame. It is the practice of asking "Why?" until the "What" becomes inevitable.

## When to Use This Skill

- Starting a new feature or major refactor
- Navigating ambiguous requirements or conflicting stakeholder needs
- Prioritizing a backlog of ideas by value vs. effort
- Identifying friction points in an existing user journey
- Designing complex interactions (canvases, workflows, multi-step forms)
- Briefing a specialist agent on the "why" behind a task

## The Core Process: Discovery to Synthesis

### 1. Stakeholder Empathy (The "Who")
Before writing code, identify the **persona**. Who is the user? What are their constraints? What is their "So What?" Use the [Persona Card Template](resources/template-persona-card.md) to define the archetype.

### 2. Problem Discovery (The "Why")
Resist the urge to jump to solutions. Use the [Discovery Questions Guide](resources/guide-discovery-questions.md) to interrogate the request. If you can't state the problem in one sentence, you haven't discovered it yet.

### 3. Clarify (The "How Exactly")
Before mapping the journey or delegating implementation, run a structured pass over every behavioral surface the feature touches. Use the [Specification Completeness Guide](resources/guide-specification-completeness.md) to catch underspecified behavior in common patterns — UI, API, workflow, and authorization alike. Use the [Contract-First Clarification](resources/guide-contract-first-clarification.md) protocol to surface unknowns, produce precise echo-check summaries, and lock the behavioral contract before delegation.

### 4. Journey Mapping (The "How")
Map the experience from trigger to completion. Where is the cognitive load highest? Where is the feedback loop silent? Use the [User Journey Map Template](resources/template-journey-map.md) to visualize the flow and identify opportunities.
When a journey is mature enough for QA verification, transform it into a Visual QA interaction script using the [Journey-to-QA Template](resources/template-journey-qa.md). The BA journey map captures human experience; the QA script captures testable interactions.

### 5. Prioritization & Value (The "What")
Define the **Minimum Viable Experience (MVE)**. What is the smallest set of features that provide 80% of the value? Use the [Value-Effort Matrix Template](resources/template-value-effort-matrix.md) to sequence the work and manage risk.

## Principles of Business Analysis

- **User Outcome > System Output**: We don't build features; we enable outcomes. A feature is only successful if the user's "So What?" is satisfied.
- **Friction is a Bug**: Every extra click, every unclear label, and every second of waiting is a friction point that erodes value.
- **Context is Everything**: A feature used once a year needs different design patterns than a feature used every five minutes.
- **Sequence Matters**: Build the hardest, most valuable part first. Polish comes after the core journey is proven.

## Resources

- [Persona Card Template](resources/template-persona-card.md) — Defining the user archetype
- [User Journey Map Template](resources/template-journey-map.md) — Mapping the experience
- [Journey-to-QA Template](resources/template-journey-qa.md) — Transforming journey maps into Visual QA scripts
- [Value-Effort Matrix Template](resources/template-value-effort-matrix.md) — Prioritizing the work
- [Product Discovery Questions](resources/guide-discovery-questions.md) — Structured thinking partner
- [Specification Completeness Guide](resources/guide-specification-completeness.md) — Pattern-organized anti-ambiguity checklist
- [Contract-First Clarification](resources/guide-contract-first-clarification.md) — Conversational protocol for locking behavioral contracts
- [Tag Taxonomy Guide](resources/guide-tag-taxonomy.md) — Label namespacing and anti-churn rules

## Cross-References

- [Product Management Skill](../product-management/SKILL.md) — Downstream feature governance and traceability
- [Planning Skill](../planning/SKILL.md) — Implementation decomposition and delegation
- [Delegation Skill](../delegation/SKILL.md) — Using business analysis to inform specialist briefs
- [The Architect Agent](../../agents/architect.md) — Technical design peer
- [Visual QA Agent](../../agents/visual-qa.md) — Executes interaction scripts derived from journey maps

</ANCHORSKILL-BUSINESS-ANALYST>
