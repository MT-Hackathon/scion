---
name: rule-authoring-patterns
description: "Governs quality patterns for Cursor rule design: glob activation, always-on rules, anchor navigation, RULE.mdc structure, token budgeting, and transfer workflows. Use when creating or refining rules, configuring file-pattern triggers, or designing rule activation boundaries. DO NOT use for skill authoring (see skill-authoring-patterns) or agent personas (see delegation)."
---

<ANCHORSKILL-RULE-AUTHORING>

# Rule Authoring Patterns

Patterns and standards for maintaining high-quality, portable Cursor rules. This skill focuses on the structural and governance aspects of rule authoring.

## Resources & Guides
- **reference-types-comparison.md**: Comparison with Skills and Agents.
- **reference-number-ranges.md**: Semantic ranges (000-999) and activation modes.
- **reference-bundling.md**: Directory layouts vs. single-file `.mdc` format.
- **reference-anchors.md**: Anchor naming conventions for navigation.
- **guide-philosophy.md**: Specificity, memory, and composability in rules.
- **reference-consolidation-patterns.md**: Overlap heuristics and token budget management.
- **checklist-pre-creation.md**: Validation gates before creating new rules.
- **guide-transfer-workflow.md**: Workflow for porting rules across projects.
- **reference-project-markers.md**: Identifying and abstracting project-specific content.
- **script-standards.md**: Canonical patterns for ecosystem scripts (uv, argparse, fallbacks).
- **guide-command-authoring.md**: Patterns for writing `.cursor/commands/*.md` — agent-facing prompts, default scope, what to strip.

## Management Scripts

| Script | Purpose |
|--------|---------|
| `generate-new-rule.py` | Scaffolding for new rule folders/files. |
| `validate-frontmatter.py` | Quality and length check for rule descriptions. |
| `scan-project-references.py` | Identifies local specifics for rule transfer. |
| `validate-transfer-ready.py` | Validates rules are ready for porting. |
| `validate-scaffolding-compliance.py` | Ensures alignment with scaffolding standards. |
| `scan-scaffolding-quality.py` | Checks for missing checklists/examples/criteria. |
| `scan-scaffolding-sizes.py` | Token counting and compliance reporting. |
| `reduce-oversized-rules.py` | Automated trimming to ≤350 tokens. |

## Script Reference

### generate-new-rule.py
Interactive rule/skill/agent scaffolding using project patterns.

`uv run generate-new-rule.py [--type <type>] [--number N] [--name <name>] [--category <cat>] [--globs <pattern>] [--always-apply] [--model <id>] [--readonly] [--background]`

| Arg | Purpose |
|-----|---------|
| `--type` | Type: rule, skill, or agent |
| `--number` | Number for rules/skills (0-999) |
| `--name` | Name in kebab-case |
| `--category` | Category: meta, code, packages, ui, workflow |
| `--globs` | Glob pattern for rule (e.g., *.py) |
| `--always-apply` | Make rule always-on |
| `--model` | Model for agent (e.g., inherit, gemini-3-flash) |
| `--readonly` | Make agent read-only |
| `--background` | Run agent in background |

### validate-frontmatter.py
Validate scaffolding rule and skill frontmatter descriptions.

`uv run validate-frontmatter.py`

### scan-project-references.py
Scan rules for project-specific content before transfer.

`uv run scan-project-references.py`

### validate-transfer-ready.py
Validate that rules are ready for transfer to a new project.

`uv run validate-transfer-ready.py`

### validate-scaffolding-compliance.py
Validate scaffolding file compliance with defined standards.

`uv run validate-scaffolding-compliance.py`

### scan-scaffolding-quality.py
Scan scaffolding files for quality issues (missing checklists, examples, etc.).

`uv run scan-scaffolding-quality.py`

### scan-scaffolding-sizes.py
Scan all scaffolding files and report accurate token counts.

`uv run scan-scaffolding-sizes.py`

### reduce-oversized-rules.py
Reduce oversized rules by compressing verbose sections.

`uv run reduce-oversized-rules.py`

## Core Governance

### Token Economics (Why the Structure Works)
Progressive disclosure saves tokens across three levels:

| Level | Cost | Purpose |
|-------|------|---------|
| Description (metadata) | 30-50t | Model decides relevance |
| Manifest (navigation) | 100-200t | Model selects what to read |
| Full content | 500-5000t | Model reads only needed details |

Without manifest navigation, models spend tokens discovering what exists. With manifest + named resources, token cost drops and response quality increases.

### Semantic Number Ranges
| Range | Activation | Purpose |
|-------|------------|---------|
| **000** | Always-on | Universal operating environment (intellectual safety, collaboration, agency) |
| **001-010** | Always-on | Coding process mandates (NASA, delegation mechanics, cascade tracing) |
| **011-099** | Description-activated | Universal non-always-on (environment, workflows, tooling) |
| **100-199** | Description + globs | Language-specific rules (Python, Rust, Java, TypeScript, Angular) |
| **200-999** | Varies | Project-specific (flexible organization) |

**Range details:**
- **000**: Universal — travels to every environment. Not coding-specific.
- **001-010**: Coding always-on — travels only to coding environments via rootstock sync policy. Always-on because planning and designing code requires these mandates even when no code files are open.
- **011-099**: Universal but task-scoped. Reserve `080-089` for universal UI patterns.
- **100-199**: Per-language. Suggested partitions: `100-109` Python, `110-119` Rust, `120-129` Java, `130-139` JS/TS core, `140-149` Angular, `150-159` SvelteKit.
- **200-999**: Flexible project-specific organization.

### Activation Patterns
| Pattern | When to Use | Example |
|---------|-------------|---------|
| `alwaysApply: true` | Every conversation, every context | `000-operating-environment`, `001-foundational` |
| `description` + `globs` | Language/domain rules needing reliable activation | `100-constitution-python` |
| `description` only | Intelligent keyword/task activation | `101-testing-debugging` |

**MANDATORY: Always include a `description` alongside `globs`.** Glob activation does not fire from agent Read tool calls — it only fires when the user has matching files open in editor tabs. During agent-driven work (which is most work), glob rules are effectively dark. The `description` field enables "Apply Intelligently" activation — the same mechanism skills use — as a reliable fallback. This was empirically verified (Mar 2026): reading `.rs` and `.py` files via the Read tool did not trigger any glob-activated rules.

Cross-language rules should use intelligent activation and move language specifics into resources.

### Bundling Strategy
Choose format by complexity:
- **Single-file (`.mdc`)**: simple guidance, no supporting scripts/resources.
- **Folder format**: required for complex guidance with resources/scripts.

```text
.cursor/rules/{number}-{name}/
├── RULE.mdc
├── resources/
│   └── {prefix}-{topic}.md
└── scripts/
```

### Anchor Naming Convention
Anchors derive from folder names in upper kebab case:
- `015-environment` -> `ANCHORRULE-ENVIRONMENT`
- `100-constitution-python` -> `ANCHORRULE-CONSTITUTION-PYTHON`

Rules:
- One anchor per active rule.
- Anchor must be unique across all rules.
- Deprecated rules should not carry anchors.

### Deprecation Pattern
When consolidating rules:
1. Set description to `DEPRECATED - Consolidated into {rule}. DO NOT USE.`
2. Remove anchor.
3. Leave minimal redirect content to new location.
4. Remove after grace period if no references remain.

### Generated Rules Lifecycle
Some rules are machine-generated and refreshed automatically — they have a fundamentally different lifecycle than authored rules. The codebase-briefing rule (999-prefix) is the canonical example: it's written by a script on session start and always overwritten.

Generated rules must never be hand-edited because the next generation cycle will overwrite any manual changes. If a generated rule needs improvement, fix the generator, not the output. Conventions:
- **999-prefix**: Reserved for auto-generated context rules
- **Read-only output**: Treat as diagnostic data, not authored knowledge
- **.gitignore**: Generated rules should be excluded from version control since they're per-user, per-session artifacts

### Cross-Runtime Rule Systems
This workspace maintains parallel rule systems for multiple AI runtimes:
- `.cursor/rules/` — Cursor IDE (`.mdc` format with YAML frontmatter)
- `.claude/rules/` — Claude Code / direct Anthropic API (markdown format)
- `.aiassistant/rules/` — JetBrains AI Assistant (markdown format)

These systems have different formats and activation mechanisms. Changes to `.cursor/rules/` do not automatically propagate to the other systems. The rootstock sync system (graft) is the canonical propagation path — it handles format conversion and distribution. When authoring a rule intended for all AI contexts, push the change through graft rather than manually mirroring.

### Resource Naming Convention (MANDATED)
Use semantic prefixes for discovery:
- `examples-` - working patterns
- `reference-` - lookup/registries
- `checklist-` - validation gates
- `guide-` - procedural workflows

Constraints: one concept per file, concise scope, avoid generic names (`patterns.md`, `notes.md`).

### Generalizable vs Project-Specific Content
Inside resources, separate:
- `## Pattern` for portable logic
- `## Project Implementation` for local paths/components/stores

This separation is mandatory for transferability and targeted cleanup.

### Redundancy Prevention (Pre-Creation Mandate)
Scan before creating any new rule:
- **>=80% overlap**: update existing rule.
- **40-80% overlap**: evaluate with consolidation heuristics.
- **<40% overlap**: create new rule with cross-references.

Use [reference-consolidation-patterns.md](resources/reference-consolidation-patterns.md) for overlap decisions.

## Rule Philosophy

### The Specificity Principle
Rules encode how this workspace works, not generic best practices.

### The Workspace Memory Pattern
Rules are operational memory that evolves with practice; conflicts between rules signal divergence that needs consolidation.

### The Portability Principle
The `.cursor` system is a portable operating environment, not repo-local clutter.

This means:
- Inert rules (globs with no current matches) are expected and low-cost.
- Do not delete inactive rules for tidiness.
- Remove only through explicit deprecation/consolidation workflow.
- Carrying dormant knowledge is cheap; losing it during project transitions is expensive.

### The Composability Principle
Rules should be narrow, ecosystem-aware, and compose automatically without manual orchestration.

### The Placement Heuristic
Rules justify their token cost against **criticality × cost-of-absence**, not frequency of use. A rare-but-critical mandate (like PowerShell quote escaping) stays as a rule if its absence causes a failure mode the agent can't recover from. Frequent-but-recoverable guidance is a skill.

The test: "If I remove this from always-on and make it a skill, what breaks?"
- If the agent will **silently produce wrong output** -> it stays as a rule
- If the agent will **stumble but self-correct** -> it's a skill
- If the agent **won't notice the absence** -> it shouldn't exist at all

### Category-Specific Resource Patterns
| Category | Number Range | Required Resources | Optional |
|----------|--------------|-------------------|----------|
| Meta/Universal | 000-099 | references + checklists | validation scripts |
| Language-Specific | 100-199 | code examples + conventions | language guides |
| Project-Specific | 200-999 | domain resources | project assets |

### How Patterns Are Discovered
1. Repeated behavior appears across sessions.
2. Pattern is codified with concrete examples.
3. Pattern is reused and pressure-tested.
4. Rule evolves with edge cases.

## Rule Transfer Workflow

### Transfer Philosophy
- `000-199` are portable.
- `200-999` are project-specific and usually archived.
- Keep structure while clearing project-local implementation details.

### Quick Start
1. Run `scan-project-references.py` to identify local specifics.
2. Follow [guide-transfer-workflow.md](resources/guide-transfer-workflow.md).
3. Validate with `validate-transfer-ready.py`.
4. Copy the prepared ruleset.

### Key Files
- `001-foundational/RULE.mdc` (project information placeholders).
- `resources/*` sections labeled `## Project Implementation`.

## Cross-References
- [create-rule](~/.cursor/skills-cursor/create-rule/SKILL.md) — Procedural creation of `.mdc` files.
- [skill-authoring-patterns](../skill-authoring-patterns/SKILL.md) — Patterns for skill design (description-based activation).
- [delegation](../delegation/SKILL.md) — Agent authoring and team orchestration patterns.
- [001-foundational](../../rules/001-foundational/RULE.mdc) — Foundational project mandates.

</ANCHORSKILL-RULE-AUTHORING>
