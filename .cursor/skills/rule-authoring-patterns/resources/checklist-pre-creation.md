# Checklist: Pre-Creation

Validation checklist before creating a new rule.

---

## Pre-Creation Checklist

- [ ] Have I searched for existing rules on this topic? (`grep -r "topic" .cursor/rules/`)
- [ ] Have I calculated the overlap percentage with existing rules?
- [ ] Is overlap <40% (justifying new rule)?
- [ ] Would this rule heavily cross-reference another? Merge instead if so.
- [ ] Are there scripts in `.cursor/rules/*/scripts/` this rule should document?
- [ ] Is the number range correct for this content type?
- [ ] Does the description have activation keywords AND negations ("DO NOT use for...")?

---

## Structure Checklist

- [ ] Folder name uses kebab-case: `{number}-{name}/`
- [ ] Main file present: `RULE.mdc`
- [ ] Anchor present and matches folder name: `<ANCHORSKILL-{NAME}>...</ANCHORSKILL-{NAME}>`
- [ ] TOC/manifest section listing resources with use-when signals
- [ ] Resources use descriptive prefixes (`examples-`, `reference-`, `checklist-`, `guide-`)
- [ ] At least one properly-prefixed resource file exists
- [ ] Resource files are 50-150 lines max (one concept per file)

---

## Activation Pattern Checklist

| Rule Type | Activation | Check |
|-----------|------------|-------|
| Always-on (000-010) | `alwaysApply: true` | [ ] |
| Language-specific (100-199) | `globs: "*.{ext}"` | [ ] |
| Task-based (all others) | `alwaysApply: false`, no globs | [ ] |

**Cross-language rules:** Use intelligent activation + language-specific resources (e.g., `examples-test-patterns-python.md`)

---

## Token Budget Checklist

| Range | Purpose | Max Budget | Check |
|-------|---------|------------|-------|
| **000-010** | Always-on universal | 250 tokens | [ ] |
| **011-099** | Universal non-always-on | 400 tokens | [ ] |
| **100-199** | Language-specific | 550 tokens | [ ] |
| **200-999** | Project-specific | 750 tokens | [ ] |

---

## Number Range Checklist

### Universal Rules (000-099)

- [ ] 000-010: Only if truly always-on (consolidate into 000 if possible)
- [ ] 011-079: Universal tooling, workflows, environment
- [ ] 080-089: Universal UI patterns (reserved)

### Language-Specific Rules (100-199)

- [ ] 100-109: Python
- [ ] 110-119: Rust
- [ ] 120-129: Java
- [ ] 130-139: JavaScript/TypeScript core
- [ ] 140-149: Angular
- [ ] 150-159: SvelteKit
- [ ] 160-199: Reserved

### Project-Specific Rules (200-999)

- [ ] Flexible organization per project needs
- [ ] No mandated sub-ranges

---

## Category-Specific Checklist

### Meta/Universal Rules (000-099)

- [ ] Has reference files with lookup data
- [ ] Has checklists for validation
- [ ] Optional: validation scripts

### Language-Specific Rules (100-199)

- [ ] Has code examples in that language
- [ ] Has naming conventions specific to language
- [ ] Uses `globs` for always-on per language
- [ ] Optional: language-specific guides

### Project-Specific Rules (200-999)

- [ ] Has project-specific examples
- [ ] Uses `## Project Implementation` sections where applicable
- [ ] Optional: varies by domain
