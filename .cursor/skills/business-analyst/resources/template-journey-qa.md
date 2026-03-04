# Journey-to-QA Interaction Script Template

Transforms a BA journey map into a Visual QA interaction script. The BA journey map asks "what is the user experiencing?" The QA script asks "what does the tester click?" They are sibling artifacts, not the same document.

## Metadata

- **Naming**: `journey-[scenario-slug].md`
- **Location**: `resources/journeys/` in the project's governing skill folder
- **Created by**: Whoever understands the feature flow (BA, developer, orchestrator)
- **Consumed by**: Visual QA agent (discovery by glob, or explicit path from orchestrator brief)

## Template

```
# Journey: [Scenario Name]

**Persona**: [Reference to Persona Card]
**Viewport**: All (375px, 768px, 1200px)
**Preconditions**: [App state required before Step 1]
**Routes touched**: [URL paths exercised — used by orchestrator for scoping]

## Steps

1. **[Entry action]** [CURRENT]: [What the user does first — always via UI element, never URL]
   - **See**: [What appears on screen]
   - **Verify**: [Specific check that confirms success]

2. **[Next action]** [CURRENT]: [Each step is a meaningful interaction]
   - **See**: [Expected visual state]
   - **Verify**: [Specific assertion]

## Error Variations

### E1. [Error scenario name]
- **At step**: [Which step triggers this]
- **Action**: [What the user does differently]
- **See**: [Expected error state]
- **Verify**: [Specific error evidence]
```

## Transformation Guide

When converting a BA journey map into this format:

- BA **Phases** (Trigger/Entry/Core Action/Validation/Completion) become **numbered Steps**
- BA **Pain Points** become **Error Variations**
- BA **Entry conditions** become the **Preconditions** header
- BA **Exit state** becomes the final step's **Verify** assertion
- **Discard** Thinking/Feeling and Opportunities — those are discovery artifacts, not test artifacts

## Sprint Markers

- `[CURRENT]` — step is testable against shipped features
- `[THIS SPRINT]` — step depends on in-progress work; observe what exists, flag gaps

## Rules

- Cap at ~10 steps per journey; split longer flows into sub-journeys
- Every page transition must happen through a visible UI element
- At least one error variation per journey
- Dark mode checkpoint: toggle theme and verify first + last step after completing the journey
