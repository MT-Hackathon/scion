---
name: linter-integration
description: "Governs linter integration for AI-human collaboration: ESLint, Checkstyle, PMD, SpotBugs configuration, layered config pattern, and personal override workflows. Use when running linters, fixing lint errors, checking code quality, or setting up linting infrastructure. DO NOT use for testing patterns (see testing-debugging) or build configuration."
---

<ANCHORSKILL-LINTER-INTEGRATION>

# Linter Integration

## Table of Contents & Resources

- [Core Concepts](#core-concepts)
- [Reference: AI Anti-Patterns](resources/reference-ai-antipatterns.md)
- [Examples: Layered Config](resources/examples-layered-config.md)
- [Checklist: Linter Workflow](resources/checklist-linter-workflow.md)

### Scripts

- **find-linter-patterns.py** - Identify common linter violations
- **find-todos.py** - Locate TODO/FIXME comments in codebase
- **check-local-config.py** - Detect if personal linter overlay exists

## Core Concepts

### Why Linters Matter for AI

Linters are force multipliers for AI-human collaboration:

1. **AI models diligently check linter output** - Models treat linter errors as actionable feedback
2. **Strict linting prevents "AI code smell"** - Magic numbers, TODOs, any types caught automatically
3. **Humans rely on linters as first-pass review** - Reduces cognitive load on reviewers
4. **Deterministic validation** - Unlike AI's probabilistic nature, linters give consistent results

Research shows AI-generated code produces 1.7x more issues than human code. Static analysis catches ~60% of AI-generated failures within minutes.

### Layered Config Pattern

Support both team standards and personal strictness:

```
eslint.config.js        <- Team's shared config (committed)
eslint.config.local.js  <- Personal stricter config (gitignored)
```

**For Python projects:**

```
ruff.toml               <- Team's shared config (committed)
ruff.local.toml         <- Personal stricter config (gitignored)
```

**For Stylelint (SCSS/CSS):**

```
.stylelintrc.json       <- Team's shared config (committed)
.stylelintrc.local.json <- Personal stricter config (gitignored)
```

If a local Stylelint overlay exists, run with `stylelint --config .stylelintrc.local.json`.

### AI Workflow (MANDATORY)

**Before making code changes:**

1. Check if personal config exists: `ls eslint.config.local.js` or `ls ruff.local.toml`
2. Note which config to use for linting

**After code edits:**

1. Run linter with appropriate config
2. If personal config exists: `npm run lint:strict` or `ruff check --config ruff.local.toml`
3. If only team config: `npm run lint` or `ruff check`
4. Fix all errors before completing task

**Reporting:**

- If personal config adds rules not in base, mention what extra checks ran
- Example: "Ran strict linting (magic numbers, no-console enabled)"

### AI-Specific Anti-Patterns to Lint

| Anti-Pattern | ESLint Rule | Ruff Rule | Stylelint Rule | Why It Matters |
|--------------|-------------|-----------|----------------|----------------|
| Magic numbers | `@typescript-eslint/no-magic-numbers` | - | - | Unclear intent, hard to change |
| TODO/FIXME left in code | `no-warning-comments` | `FIX` | - | Incomplete work shipped |
| `any` type | `@typescript-eslint/no-explicit-any` | - | - | Defeats type safety |
| console.log | `no-console` | `T201` | - | Debug code in production |
| Unused variables | `no-unused-vars` | `F841` | - | Dead code accumulation |
| Hardcoded colors | - | - | `color-no-hex`, `color-named` | Avoid theme drift and inconsistency |
| Hardcoded spacing | - | - | `scale-unlimited/declaration-strict-value` | Use design tokens for consistency |
| Hardcoded strings | - | - | - | Use constants or i18n |

### Design Token Enforcement (Stylelint)

The `stylelint-declaration-strict-value` plugin enforces design token usage:

```json
"scale-unlimited/declaration-strict-value": [
  ["/margin/", "/padding/", "gap", "row-gap", "column-gap", "border-radius"],
  {
    "ignoreValues": {
      "": ["0", "1px", "2px", "3px", "auto", "inherit", "initial", "unset"],
      "border-radius": ["0", "1px", "2px", "3px", "50%", "inherit", "initial", "unset"]
    }
  }
]
```

**What it enforces:**
- Margin, padding, gap, and border-radius must use `var(--app-*)` tokens
- Micro values (1-3px), zero, and CSS keywords are allowed
- Theme files and animation-specific files are excluded

**When you see this error:**
```
Expected design token (var(--app-*)) for "16px" of "padding".
```

Replace with the appropriate token from `src/style.scss`:
- `4px` -> `var(--app-spacing-xs)`
- `8px` -> `var(--app-spacing-sm)`
- `12px` -> `var(--app-spacing-md-sm)`
- `16px` -> `var(--app-spacing-md)`
- `24px` -> `var(--app-spacing-lg)`
- `32px` -> `var(--app-spacing-xl)`

### Python Linting (Ruff + mypy)

Python linting for the Universal-API backend and rule/skill scripts:

- **Primary tool**: `ruff check src/` for style and correctness
- **Type checking**: `mypy src/` for type safety
- **Config**: `pyproject.toml` or `ruff.toml`
- **Auto-fix**: `ruff check --fix src/`
- **Full check**: `ruff check src/ && mypy src/`

### Java Linting (Gradle)

Backend linting runs through Gradle tasks in the `procurement-api` repo:

```
./gradlew checkstyleMain checkstyleTest   # Style + coding rules
./gradlew spotbugsMain                     # Null safety, unchecked returns
./gradlew check                            # All of the above + tests + JaCoCo
```

Key Checkstyle rules: `IllegalCatch` (broad exception catches), `MethodLength` (>60 lines), `MagicNumber`.
Key SpotBugs detectors: `NP_NULL_ON_SOME_PATH` (NPE risk), `RCN_REDUNDANT_NULLCHECK` (redundant null check).

### Semantic Spacing Tokens (current values)
- `--app-spacing-card-padding`: 16px (uses `--app-spacing-md`)
- `--app-spacing-section-gap`: 24px (uses `--app-spacing-lg`)
- `--app-spacing-form-gap`: 12px (uses `--app-spacing-md-sm`)

### Border Tokens (prefer borders over shadows for grounded elements)
- `--app-border-subtle`: 1px solid with 60% outline-variant opacity
- `--app-border-default`: 1px solid outline-variant

See [angular-forms-material](../angular-forms-material/SKILL.md) for complete token reference.

### npm Scripts Convention

```json
{
  "lint": "eslint src/ && npm run lint:styles",
  "lint:strict": "eslint --config eslint.config.local.js src/",
  "lint:fix": "eslint src/ --fix && npm run lint:styles:fix",
  "lint:strict:fix": "eslint --config eslint.config.local.js src/ --fix",
  "lint:styles": "stylelint \"src/**/*.scss\"",
  "lint:styles:fix": "stylelint \"src/**/*.scss\" --fix"
}
```

### When to Use Stricter Personal Config

Personal overlay is valuable for:

- **AI-assisted development** - Catches more AI-generated issues
- **Learning new patterns** - Stricter rules teach better habits
- **Pre-review quality gate** - Clean up before team sees code
- **Experimental strictness** - Test rules before proposing to team

## Cross-References

**Related rules:**

- [012-constitution-universal](../../rules/012-constitution-universal/RULE.mdc) - Forbidden patterns that linters enforce
- [environment](../environment/SKILL.md) - Environment setup including linter tools
- [angular-forms-material](../angular-forms-material/SKILL.md) - Form patterns plus theme tokens and palette usage
- [130-constitution-typescript](../../rules/130-constitution-typescript/RULE.mdc) - TypeScript-specific rules

## Script Reference

### check-local-config.py
Check for personal linter config overlays (ESLint/Ruff).

`uv run check-local-config.py [path]`

| Arg | Purpose |
|-----|---------|
| `[path]` | Project path to check for configs (default: .) |

### find-linter-patterns.py
Identify common linter violations and patterns to fix.

`uv run find-linter-patterns.py [--path PATH] [--ts|--py|--all]`

| Arg | Purpose |
|-----|---------|
| `--path PATH` | Directory to scan (default: .) |
| `--ts` | Filter for TypeScript files |
| `--py` | Filter for Python files |
| `--all` | Search all supported files (default) |

### find-todos.py
Locate TODO/FIXME comments with context and file locations.

`uv run find-todos.py [--path PATH] [--patterns PATTERN] [--strict]`

| Arg | Purpose |
|-----|---------|
| `--path PATH` | Directory to scan (default: .) |
| `--patterns` | Custom TODO patterns (default: TODO\|FIXME\|HACK\|XXX) |
| `--strict` | Exit 1 when any TODOs are found (CI mode) |


</ANCHORSKILL-LINTER-INTEGRATION>
