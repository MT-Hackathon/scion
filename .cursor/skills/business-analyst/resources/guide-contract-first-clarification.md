# Contract-First Clarification

Contract-First Clarification is a conversational protocol for establishing mutual understanding before execution begins. It treats the interaction between human and AI as a negotiation where "LOCKED" status is earned through precision, not assumed by proximity.

This protocol adapts Nate B Jones' "contract-first prompting" (August 2025) for our multi-agent workflow, ensuring that specification unknowns are surfaced by the Orchestrator and resolved before they become implementation rework for the Executor.

## The Protocol

### 1. Specification Review
Start by reflecting the feature plan as currently understood. State **who** the user is, **what** capability is being added, and **why** it matters. This provides a baseline for correction; if the Orchestrator’s summary is wrong, the "contract" is already broken.

*Example*: "We are building a Vendor Search feature for Agency Buyers so they can quickly find verified suppliers by name or status without leaving the procurement dashboard."

### 2. Structured Interrogation
Walk the [Specification Completeness Guide](guide-specification-completeness.md) pattern-by-pattern for every behavioral surface the feature touches. For each relevant pattern (Lists, Search, Forms, APIs, Workflows, Permissions, etc.), systematically answer the required questions.

Record these answers inline. Any answer that is "I don't know yet" or "Follow default" must be flagged as an **ambiguity hotspot**. Do not proceed to planning until these hotspots are either resolved or explicitly capped as "Executor's Choice" in the brief.

### 3. Echo Check
For each behavioral surface, produce a single-sentence summary of what it *actually does* based on the interrogation. This forces precision and exposes "handwave" language that hides complexity.

*   **Before (Vague)**: "Users can search for vendors."
*   **After (Precise)**: "Users can filter the vendor list by name (contains match) and status (exact match), with results updating on 300ms debounce, persisted in URL query params, showing 'No vendors match your filters' when empty."

### 4. Contract Lock
The answers and echo-check summaries feed directly into the delegation brief. The Orchestrator must include a **Behavioral Contract** section with status **LOCKED** when behavior is being specified.

**Trigger Rules for LOCKED Status**:
A contract must be LOCKED (and thus interrogated) if the change involves:
- User-visible flow or UI behavior (including empty, loading, or error states)
- List, search, or filter semantics
- Form validation or business rules
- CRUD side effects or destructive actions (e.g., "Delete" confirmation text)
- API request/response or error semantics
- Permissions, roles, or state-transition behavior

If the work is pure infrastructure or refactoring with no behavioral change, the status is **N/A** with a short rationale.

### 5. Amendment Protocol
If implementation reveals a gap the clarification missed, the "Spec-First, Code-Second" rule applies:
1. **Stop** implementation on that specific surface.
2. **Update** the specification (the echo-check summary) to reflect the new decision.
3. **Resume** implementation.

The specification remains the source of truth; the code is merely the realization of the contract.

## Recognizing Handwave Language

"Handwave" language consists of high-level verbs that assume a shared mental model which doesn't exist. When you hear these, dig deeper:

- **"Users can search..."** → Search by what fields? Matches are exact or fuzzy? Where do results appear?
- **"Show a list of items..."** → Which columns? What order? What happens if the list is empty?
- **"Add validation..."** → To which fields? What rules (regex, length, required)? When does it fire (blur or change)?
- **"Handle errors gracefully..."** → Which specific errors (401, 403, 500)? What does the user see? Is there a retry?
- **"Make it responsive..."** → What are the breakpoints? What stacks, what hides, and what shrinks?
- **"Add an endpoint for..."** → What are the request/response shapes? What errors can it return? Is it paginated? Idempotent?
- **"Route it through approval..."** → Which roles approve? What happens on rejection? Can it be reversed? What side effects fire?
- **"Restrict access to..."** → Which roles? Scoped how (global, agency, team)? What does denial look like? Hidden or disabled?

## Sources
Adapted from Nate B Jones, "Stop Letting AI Guess" (August 2025). Jones' original methodology focuses on human-to-LLM "contract-first prompting" to reduce hallucination and rework; we apply it here to the Orchestrator-Executor delegation boundary.
