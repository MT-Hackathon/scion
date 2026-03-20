# Ogham Curation Protocol

This protocol defines the step-by-step workflow for a human-initiated curation session to maintain the health and resonance of the Ogham memory corpus.

## Curation Workflow

1. **Inventory the Kinds**
   List all memories grouped by kind. Evaluate the distribution. A healthy corpus should not be more than 60% `learning` and `correction`. If it is, look for opportunities to promote technical gotchas into skills.

2. **Audit for Accuracy**
   Flag all `learning` and `correction` memories older than 60 days. Are these still true? Has the codebase evolved past them? Archive or supersede any entries that are no longer accurate or relevant.

3. **Promote to Skills or Rules**
   Identify memories that have converged into behavioral mandates or reusable technical patterns. 
   - Move mandates to `.cursor/rules/`.
   - Move technical patterns to the `resources/` or `blueprints/` of the relevant `.cursor/skills/`.

4. **Identify Supersedable Entries**
   Search for memories in overlapping domains. If two memories cover the same topic but from different sessions, merge them into a single entry and supersede the older one.

5. **Build Constellations**
   Identify unlinked memories. Use `link_memory` to connect related entries (e.g., a `decision` to the `insight` that informed it, or a `correction` to the `learning` that prevented its recurrence).

6. **Refine the Discovery Surface**
   Review the tags for each memory. The tag vocabulary is the primary discovery surface for FTS and tag-matching. Ensure tags are consistent, specific, and descriptive.

7. **Review High-Activation Entries**
   Identify memories with high activation scores that are also old. These are "load-bearing" memories. Decide if they should be promoted to the permanent layer (rules/skills) or if their activation is a signal of a persistent problem that needs an architectural fix.

## Curation Rubric for Promotion

- **Promote to Rule**: If the knowledge is an invariant that must *never* be violated (e.g., "Always use X for Y").
- **Promote to Skill**: If the knowledge is a procedure or pattern that should be *available* when working in a domain (e.g., "How to handle X in Svelte 5").
- **Keep as Memory**: If the knowledge is specific to the *history, texture, or particular decisions* of this project that doesn't fit a general pattern.
