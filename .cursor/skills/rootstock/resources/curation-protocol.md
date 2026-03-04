# Curation Protocol

## Purpose

This document defines the curation protocol for Rootstock: the classification taxonomy, quality rubric, structured output contract, trust boundaries, and anti-pattern guards. It is referenced by the curator agent in Cursor and embedded in prompts for GitLab Duo via `curate.py`. Both backends must produce identical output format.

## Classification Taxonomy

### Evolution

Small refinement to existing knowledge.

Decision criteria:
- Does it actually improve on what exists?
- Is it more token-efficient?
- Does it teach the mechanism or just restate?
- Is the change high nuance with small token movement?

Recommendation:
- `accept` if demonstrably better
- `reject` if lateral or worse

### New Artifact

Entirely new rule, skill, or script.

Decision criteria:
- Could this knowledge integrate into an existing skill rather than standing alone? Check the knowledge map for concept overlap before classifying as New Artifact. Integration into an existing skill is preferred over creating a new one — one comprehensive domain skill beats three narrow technique skills.
- Does it duplicate existing knowledge under a different name?
- Is rule vs skill vs script placement correct (always-fire vs agent-selected vs executable)?
- Does the manifest entry have proper trigger keywords, cross-references, and progressive disclosure?

Recommendation:
- `accept` if genuinely new, well-placed, and cannot integrate into existing knowledge
- `move` if misplaced or should integrate into an existing skill (specify target)
- `reject` if duplicative

### Script Change

Modification to an existing script or addition of a new script.

Decision criteria:
- Is the script portable across OS, project, and user?
- Are args documented?
- Does the manifest reflect the interface?
- Is it PEP 723 compliant?
- Does it follow existing conventions (`argparse`, `pathlib`, structured output)?

Recommendation:
- `accept` if correct
- `revise` if conventions are missed

### Reorganization Candidate

Content exists in the wrong location.

Decision criteria:
- Rule content that should be a skill (always-fire knowledge that is actually agent-selected)
- Prose that should be a script (instructions that could be automated)
- Content that should merge into an existing artifact rather than stand alone

Recommendation:
- `move` with explicit target location

### Regression

Change degrades quality.

Decision criteria:
- Bloats token count without teaching new mechanism
- Stacks curt orders instead of explaining reasoning
- Breaks progressive disclosure (front-loads detail that belongs in `resources/`)
- Removes useful cross-references
- Adds ambiguity

Recommendation:
- `reject` with specific rubric violation cited

### Prune Candidate

Knowledge should be removed.

Decision criteria:
- Superseded by other changes in this or previous cycles
- No longer accurate (deprecated APIs, removed features)
- Redundant with content elsewhere in the canonical environment

Recommendation:
- `prune` with reference to what supersedes it

## Quality Rubric

These criteria apply to all changes:

- **Token efficiency**: Does this change earn its tokens? Every token in the canonical environment is paid on every conversation that loads it. Growth must be justified by genuine new knowledge.
- **Placement correctness**: Rules are always-fire only (always-on or glob-activated). Skills are agent-selected via description keywords. Scripts are executable limbs within skills. Content in the wrong type is a Reorganization candidate.
- **Progressive disclosure**: Top-level `SKILL.md` and `RULE.mdc` stay lean. Technical detail lives in `resources/`. Scripts carry inline documentation through PEP 723 metadata and `argparse`.
- **Mechanism-teaching vs order-stacking**: Good knowledge teaches why and how. Bad knowledge stacks imperatives without reasoning. "Always use X" is an order. "Use X because Y, which prevents Z" teaches mechanism.
- **Description quality**: Descriptions are the activation mechanism — if they are vague, knowledge exists but is never found; if they overlap, the wrong skill loads. Each skill's ~50-token description budget must be fully used with trigger-heavy keywords and explicit "Use when / DO NOT use" delineation. Evaluate on every curation cycle: are trigger keywords specific and unambiguous? Does the description overlap dangerously with other skills? Would the AI actually find this skill when the domain is relevant? Saving tokens on descriptions defeats the entire progressive discovery mechanism.
- **Manifest accuracy**: Script manifests must list args and paths accurately. Skill cross-references must point to current locations.

## Structured Output Contract

Every curation recommendation must follow this schema:

```json
{
  "change_id": "string — stable identifier derived from file path + diff hash",
  "artifact_path": "string — path relative to .cursor/",
  "artifact_type": "rule | skill-knowledge | skill-script | skill-resource | agent | hook | config",
  "classification": "Evolution | NewArtifact | ScriptChange | Reorganization | Regression | Prune",
  "recommendation": "accept | revise | reject | move | prune",
  "confidence": "number 0.0-1.0",
  "target_location": "string | null — destination path if recommendation is 'move'",
  "rationale": ["string[] — concise reasons citing specific rubric criteria"],
  "violations": ["string[] — rubric criteria violated, if any"],
  "requires_human_review": "boolean — true if confidence < 0.7 or classification is ambiguous"
}
```

## Trust Boundary Rules

### Temporal-self Pipeline (rule 998)

The hooks, scripts, and skill infrastructure that build temporal-self artifacts (`ingest.py`, `segment.py`, `mine.py`, `portrait.py`) sync through Rootstock. The artifacts they produce (`self.db`, portrait text in `RULE.mdc`, session data) do not sync because they are per-user and per-project.

When evaluating changes to these scripts, assess them as shared infrastructure. Do not classify changes as regressions because output artifacts are absent from the repository.

### Codebase-sense (rule 999)

The same boundary applies. The `briefing.py` script and supporting libraries sync; generated briefing text in `RULE.mdc` does not. Briefings are project-specific and regenerated locally.

### General Principle

The tools sync; the artifacts they produce do not. Evaluate tools by interface quality, portability, and correctness, not by the presence or absence of generated output.

## Escalation Conditions

- Confidence below `0.7` -> flag for human review
- Conflicting recommendations across related changes -> escalate to cross-cluster reconciliation
- Structural or architectural question about the curation system itself -> escalate to The Architect
- Two contributors evolve the same artifact in incompatible directions -> flag as conflict and do not auto-resolve

## Anti-Pattern Guards

- **Score inflation**: LLMs tend to over-approve. Guard: If you cannot articulate why a change is better than what exists, classify it as Regression. The default stance is skeptical, not permissive.
- **Context dilution**: More context degrades judgment quality. Guard: each curation call should include only changed files and their nearest canonical neighbors, not the full environment.
- **Transitivity inconsistency**: In multi-contributor reviews, ensure A > B and B > C implies A > C. Guard: run a cross-cluster reconciliation pass to catch contradictory recommendations.
- **Explanation gap**: Stated rationale may not match actual decision factors. Guard: rationale must cite specific rubric criteria. Generic praise ("well-structured", "clean code") is insufficient.
- **Anchoring**: First-reviewed changes can become implicit baseline. Guard: vary review order across cycles and do not assume the first change defines quality.
