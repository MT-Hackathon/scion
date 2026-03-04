# design

Let's enter our thinking room. We're figuring something out together before any code gets written.

Use explorers and researchers to gather the material our conversation needs — don't rush to an answer with what you already know. We aren't in a hurry to build; we need to solidify requirements, acceptance criteria, a delegation plan, and anything we aren't confident about before making a formal plan.

The Architect is available as a peer consultant — bring them in when a trade-off needs a second opinion, not just when you're stuck. Multiple rounds are fine.

For features with behavioral surfaces, walk the [business-analyst skill](../skills/business-analyst/SKILL.md) and its [Specification Completeness Guide](../skills/business-analyst/resources/guide-specification-completeness.md) before converging — the questions that don't get answered here become TODOs in code. Use the [Contract-First Clarification](../skills/business-analyst/resources/guide-contract-first-clarification.md) protocol to lock behavioral specifics.

## Required Outputs

The output we're converging on is a plan artifact written to `.cursor/plans/<slug>.md`. Use the template at [`../skills/planning/resources/template-plan-artifact.md`](../skills/planning/resources/template-plan-artifact.md).

The plan artifact is non-negotiable and must contain all of the following — nothing is optional:

1. **Requirements and Acceptance Criteria** — each marked `LOCKED` (behavioral contract confirmed) or `N/A` with rationale (pure infrastructure/refactoring)
2. **Cascade Analysis** — three orders of effect: direct dependents, consequential modules, conditional failures. One identified risk per order minimum, or explicitly state unknown with a verification step.
3. **Risk Inventory** — identified risks with verification steps
4. **Delegation Structure** — who handles each phase, handoff criteria, and verification command

The plan must be self-contained enough that a `/build` invocation in a new thread can execute it without reconstructing our reasoning.
