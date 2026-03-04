---
name: skill-authoring-patterns
description: "Quality standards for skill authoring: folder structure, SKILL.md governance, progressive disclosure, blueprint design, resource naming, script standards (uv + PEP 723), and cross-reference hygiene. Use when creating, auditing, or refactoring any skill. DO NOT use for rule-specific design or agent delegation workflows."
---

<ANCHORSKILL-SKILL-AUTHORING>

# Skill Authoring Patterns

Design patterns for authoring high-quality skills that stay discoverable, portable, and cheap to operate over time.

## Table of Contents

- [Folder Structure](#folder-structure)
- [Knowledge Types](#knowledge-types)
- [The Blueprint Pattern](#the-blueprint-pattern)
- [SKILL.md Quality Patterns](#skillmd-quality-patterns)
- [When to Use Skill vs Rule vs Agent](#when-to-use-skill-vs-rule-vs-agent)
- [Script Policy for Skills](#script-policy-for-skills)
- [Activation Strategy](#activation-strategy)
- [Cross-References](#cross-references)

## Folder Structure

A skill is not just a markdown file. It is a small knowledge system where placement determines how much context the agent must load to act correctly.

```text
skill-name/
├── SKILL.md            ← governance: what to do, why, when (≤500 lines)
├── scripts/            ← executable automation (PEP 723, uv run --script)
├── resources/          ← narrated knowledge (prose + code blocks, explains WHY)
│   ├── examples-*      ← working patterns with explanation
│   ├── reference-*     ← lookup tables, source pointers, registries
│   ├── guide-*         ← procedural workflows
│   └── checklist-*     ← validation gates
└── blueprints/         ← structural code (real files, 20-100 lines)
```

Why this structure matters:
- `SKILL.md` is the catalog entry and decision surface. If it becomes an encyclopedia, activation cost rises and discoverability falls.
- `resources/` holds explanation-rich material that teaches mechanism and trade-offs. This keeps narration available without inflating the primary skill body.
- `blueprints/` stores working structural code so the agent can adapt from real scaffolding instead of reconstructing shape from prose.
- `scripts/` carries repeatable automation when a procedure is too fragile to execute from text instructions alone.

When each directory is needed:
- `resources/` is required once the skill needs more than concise governance in `SKILL.md`. If omitted, nuanced reasoning has nowhere to live.
- `blueprints/` is required when structural patterns repeat and prose-only examples lead to inconsistent implementations.
- `scripts/` is optional until there is repeated operational work that is deterministic and better executed than described.

The structure is a progressive disclosure system:
- front door: `SKILL.md` (fast routing and intent)
- deeper reasoning: `resources/` (teaching and reference)
- direct adaptation: `blueprints/` (structural code skeletons)
- execution: `scripts/` (automated paths)

## Knowledge Types

| Type | Purpose | Agent behavior at read time | Token cost | When to use | When NOT to use |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `SKILL.md` | Governance, boundaries, activation cues | Scans first, decides whether and how to proceed | Lowest ongoing cost when concise | Define scope, intent, and reasoning guardrails | Long examples, exhaustive tables, or full implementations |
| `resources/` | Narrated knowledge, rationale, procedural detail | Reads selectively based on need | Medium, pay-as-needed | Explain why patterns exist, provide checklists and references | Repeating governance that belongs in `SKILL.md` |
| `blueprints/` | Real structural code for adaptation | Copies/adapts scaffolding directly | Low-to-medium; high leverage | Reusable architecture skeletons (component, endpoint, workflow shape) | Domain-specific one-offs or giant full applications |
| `scripts/` | Executable automation for repeatable tasks | Runs command path instead of manual reasoning | Front-loaded authoring, low runtime ambiguity | Deterministic transformations, audits, or structured output generation | Exploratory tasks where judgment dominates |

### The Blueprint Pattern

Blueprints are real code files in `blueprints/`, not markdown examples embedded in prose.

Header convention:

```python
# BLUEPRINT: crud-endpoint
# STRUCTURAL: route decorator, request/response models, error handling shape
# ILLUSTRATIVE: entity name, field names, validation rules (replace with your domain)
```

Why blueprints are distinct from `resources/examples-*`:
- `resources/examples-*` teach reasoning, constraints, and context.
- `blueprints/` provide executable shape with placeholders.
- The first teaches when and why to apply a pattern; the second accelerates how to instantiate it safely.

Why this saves reasoning tokens:
- The agent spends fewer tokens deriving architecture from text when a valid skeleton already exists.
- Structural decisions become explicit and reusable, reducing variation and preventing accidental omission of required seams.
- Adaptation beats invention for recurring scaffolding.

Blueprint rules:
- Keep each blueprint between 20 and 100 lines so it is complete enough to adapt and small enough to scan quickly.
- Separate stable architecture from replaceable domain details using `STRUCTURAL` and `ILLUSTRATIVE` headers.
- Prefer one blueprint per recurring pattern family rather than one giant "kitchen sink" file.

Source pointer pattern:
- When a complete in-repo implementation is useful but too large to duplicate, place a source pointer in `resources/reference-*.md`.
- Example pointer language: "For a complete example of complex list management with sorting, pagination, and drawer integration, see `app/frontend/src/lib/ui/frameworks/ListPage.svelte`."
- In same-repo skills, source pointers avoid copy drift. In portable skills, keep a small blueprint skeleton so pattern utility survives relocation.

## SKILL.md Quality Patterns

### 1. The Description (Frontmatter)

The description is the primary activation mechanism and the single most important line in a skill. The budget is about 50 tokens: small enough to force clarity, large enough to express scope. A weak description makes a skill effectively invisible, because discoverability happens through this field before any body content is read.

Field constraints:
- `name`: max 64 characters, lowercase hyphens (`[a-z0-9-]`)
- `description`: max 1024 characters

Description requirements:
- **Third-person**: "Provides...", "Governs...", "Implements..."
- **Trigger-heavy**: include high-probability domain keywords and tool names where relevant
- **Delineated**: include "Use when / DO NOT use" to prevent overlap
- **Scope-clean**: mention adjacent skills when exclusion boundaries matter

Why this is non-negotiable:
- Discovery quality is upstream of all content quality; a perfect body that never loads has zero value.
- Overlapping descriptions produce misrouting, which wastes tokens and creates contradictory behavior.

Strong vs weak examples:
- Strong: "Governs Angular HttpClient patterns, RxJS pipelines, retries, and interceptors. Use when implementing API services or async data streams. DO NOT use for auth/session controls (see security)."
- Weak: "Contains HTTP tips."

### 2. The Body

`SKILL.md` is governance, not storage. Its job is to orient the agent (what are the rules?), list what's available (manifests), and point to related skills.

What MUST be in `SKILL.md`:
- **Governance**: decision criteria, constraints, patterns — the part you always need for this domain
- **Manifests**: brief listing of resources, scripts, and blueprints — enough to route, not enough to replace reading the file
- **Cross-references**: related skills with directional context

What MUST NOT be in `SKILL.md`:
- Code examples longer than ~10 lines (→ `blueprints/` or `resources/`)
- Procedural guides (→ `resources/guide-*`)
- Reference tables longer than ~10 rows (→ `resources/reference-*`)
- Checklists (→ `resources/checklist-*`)

Size guidance:
- Most well-structured skills land between 40 and 150 lines. If approaching 200, audit for content that belongs in `resources/`.
- The hard ceiling is 500 lines, but reaching it signals the skill is trying to be an encyclopedia. If Anthropic's empirical test applies — "if the agent ignores rules, the file is too long" — then attention quality, not line count, is the real constraint.
- Table of Contents required at 100+ lines.
- Anchor tag required for targeted reading.

Manifest format — resource and blueprint entries should be ~15 tokens: a brief descriptor that tells the agent whether to read the file, not a summary of its content:

```markdown
## Resources
- **checklist-skill-quality.md** — audit criteria for skill curation
- **reference-implementations.md** — source pointers to working code
```

Script manifest entries should be ~10 tokens — a verb phrase describing what the script does:

```markdown
| Script | Purpose |
|--------|---------|
| `briefing.py` | Generate codebase structural briefing |
```

Progressive disclosure pattern:
- mandatory orientation in `SKILL.md`
- deep context in `resources/guide-*` and `resources/reference-*`
- adaptation-ready scaffolding in `blueprints/`

### 3. Quality Rubric

Use this rubric to evaluate skill quality consistently.

| Dimension | Pass criteria | Fail signals |
| :--- | :--- | :--- |
| Description quality | Third-person, trigger-rich, explicit "Use when / DO NOT use", about 50 tokens, scope boundaries clear | Vague language, no delineation, overloaded overlap terms, no trigger terms |
| Folder structure | `SKILL.md` focused on governance; `resources/`, `blueprints/`, `scripts/` added when justified by content type | Everything crammed into `SKILL.md`; no place for rationale or reusable scaffolds |
| Progressive disclosure | Core file stays concise; deep details moved to `resources/`; architecture skeletons in `blueprints/` | Long operational minutiae in core file; duplicated details across files |
| Cross-references | Relevant links present; all paths relative; references resolve; no machine-local absolute paths | Broken links, absolute local paths, missing adjacent-skill boundaries |
| Blueprint quality (if present) | Real code files, 20-100 lines, `STRUCTURAL/ILLUSTRATIVE` header comments, pattern is reusable | Markdown-only pseudo-code, oversized files, no header contract, domain-hardcoded internals |

Practical audit flow:
1. Evaluate description first. If discovery fails, stop and rewrite it.
2. Check body length and ToC threshold.
3. Validate placement decisions (`resources/`, `blueprints/`, `scripts/`) against actual content.
4. Verify cross-reference portability.
5. Sample one blueprint and one resource for mechanism clarity.

## When to Use Skill vs Rule vs Agent

| Type | Best for | Activation | Content |
| :--- | :--- | :--- | :--- |
| **Skill** | Domain expertise, specialized capabilities, reusable scripts, adaptation patterns | Description-based (keyword trigger) | Governance, resources, blueprints, scripts |
| **Rule** | Always-on constraints, universal safety invariants, lint-like hard boundaries | File-pattern (glob) or always-on | Mandatory constraints and non-optional standards |
| **Agent** | Persona-based delegation, workflow ownership, high-level execution strategy | Explicit delegation | Role instructions, workflow behavior, quality responsibilities |

Placement heuristic: criticality x cost-of-absence.
- If removing guidance from always-on context causes silent wrong output, it belongs in a rule.
- If removal causes stumbling but the agent can self-correct through search and context, it belongs in a skill.
- Rule placement is justified by failure severity and detectability, not by frequency of use.

## Script Policy for Skills

Skills are the primary home for utility scripts that bridge the gap between AI guidance and local execution.

### When to Add Scripts
- Use scripts for complex data transformations, validation, or bulk operations where instructions would be too long or error-prone.
- Prefer scripts for tasks requiring structured output (`json` or `csv`) that other tools might consume.

### Script Standards
- **Environment**: use `uv` for Python scripts to ensure reproducible environments.
- **PEP 723**: include inline metadata for dependencies in Python scripts.
- **Non-interactive**: scripts must support non-interactive execution (flags, not prompts).
- **Structured Output**: prefer machine-readable output, with clean human-readable summaries as needed.

## Activation Strategy

### Keyword Optimization
Skills load from description text. Specific language increases precision and reduces false activations.
- Weak: "Helpful things for Java"
- Strong: "Spring Boot REST API patterns, JPA entity mapping, and Gradle build troubleshooting."

### Avoiding Overlap
- Audit description boundaries across `.cursor/skills/` periodically.
- If two skills co-activate for different reasons, tighten exclusion language in both descriptions.
- Keep "Use when / DO NOT use" mutually informative, not generic.

### Location
- Project skills: `/.cursor/skills/` inside the repository for domain-specific logic.
- Personal skills: `~/.cursor/skills-cursor/` for reusable cross-project patterns.

## Cross-References

- [rule-authoring-patterns](../rule-authoring-patterns/SKILL.md): patterns for rule design and activation boundaries.
- [delegation](../delegation/SKILL.md): agent authoring and delegation workflows.

</ANCHORSKILL-SKILL-AUTHORING>
