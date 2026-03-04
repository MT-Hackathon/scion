---
name: refactoring
description: "Provides refactoring utilities for bulk text replacement, function renaming, and import path updates. Use when renaming symbols, moving imports, or performing bulk text replacements across the codebase. DO NOT use for code architecture (see planning) or git operations (see git-workflows)."
---

<ANCHORSKILL-REFACTORING>

# Refactoring

Refactoring utilities for safe, repeatable bulk edits with preview-first workflows.

## Contents

- [When to Use](#when-to-use-this-skill)
- [Core Workflow](#core-workflow)
- [Scripts](#scripts)
- [Resources](#resources)
- [Cross-References](#cross-references)

## When to Use This Skill

- Renaming functions or variables across multiple files
- Performing bulk text replacements with regex patterns
- Updating import paths after file moves or module renames
- Running batch rename patterns (for example, suffix cleanup)
- Previewing diffs before applying broad mechanical edits

## Core Workflow

### 1. Scope the Change

1. Define the narrowest valid target path for the refactor
2. Choose the script that matches the operation type
3. Start in preview mode (default behavior for the argparse-based scripts)

### 2. Review Preview Output

1. Inspect file-level diffs and replacement counts
2. Confirm no unintended files are included
3. Adjust pattern/path arguments until the preview is clean

### 3. Apply and Validate

1. Re-run with `--apply` when supported
2. Run a cleanup search for stale symbols/imports
3. Run lint/test checks appropriate for the touched code

## Scripts

### find-replace-bulk.py

Preview or apply regex-based find/replace across files discovered with ripgrep.

`uv run .cursor/skills/refactoring/scripts/find-replace-bulk.py <find_pattern> <replace_text> [path] [file_type] [--apply]`

| Arg | Purpose |
|-----|---------|
| `<find_pattern>` | Regex pattern to find |
| `<replace_text>` | Replacement text |
| `[path]` | Directory path to scan (default: `.`) |
| `[file_type]` | Optional ripgrep `--type` filter (for example: `py`, `ts`) |
| `--apply` | Apply file edits (default is preview-only) |

### rename-function-safely.py

Preview or apply function-symbol renames across files that reference the old symbol.

`uv run .cursor/skills/refactoring/scripts/rename-function-safely.py <old_name> <new_name> <source_file> [--apply]`

| Arg | Purpose |
|-----|---------|
| `<old_name>` | Existing function name |
| `<new_name>` | New function name |
| `<source_file>` | File containing the function definition (validated for existence) |
| `--apply` | Apply file edits (default is preview-only) |

### update-import-paths.py

Preview or apply import-path text updates on import-related lines only (`import` / `from` lines).

`uv run .cursor/skills/refactoring/scripts/update-import-paths.py <old_import> <new_import> [path] [--apply]`

| Arg | Purpose |
|-----|---------|
| `<old_import>` | Old import text to replace |
| `<new_import>` | New import text |
| `[path]` | Directory path to scan (default: `.`) |
| `--apply` | Apply file edits (default is preview-only) |

### remove_function_suffix.py

Batch rename Python functions by removing the `_function` suffix and updating references.

`uv run .cursor/skills/refactoring/scripts/remove_function_suffix.py`

| Arg | Purpose |
|-----|---------|
| `(none)` | This script takes no command-line arguments |

| Behavior | Details |
|----------|---------|
| Discovery | Scans Python files under `src/app`, `tests`, and `src` from project root |
| Rename rule | Renames `*_function` definitions to remove the suffix |
| Guardrail | Skips names containing `_system` |
| Validation | AST parse check before write |
| Output | Per-file rename summary plus total files/definitions/replacements |

## Resources

- [Foundational Rule](../../rules/001-foundational/RULE.mdc) - Governance mandates for search-first and refactor cleanup

## Cross-References

- [SEARCH FIRST](../../rules/001-foundational/RULE.mdc) - Search before any change
- [REFAC CLEANUP](../../rules/001-foundational/RULE.mdc) - Global search after move/rename
- [Planning Skill](../planning/SKILL.md) - Architectural decomposition and strategy
- [Git Workflows Skill](../git-workflows/SKILL.md) - Git and PR operations

</ANCHORSKILL-REFACTORING>
