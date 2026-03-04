# scaffold-review

**Default scope**: scaffold files changed since the last commit (`git diff HEAD~1 --name-only`). If the invocation names specific files or a commit range, use those instead.

**Step 1 — Identify changed scaffold files**: From the diff, identify files by type:
- `SKILL.md` files → governed by the skill-authoring-patterns skill
- `RULE.mdc` files → governed by the rule-authoring-patterns skill
- `commands/*.md` files → governed by `.cursor/skills/rule-authoring-patterns/resources/guide-command-authoring.md`
- `scripts/*` files → check for PEP 723 inline metadata and `uv run --script` portability

**Step 2 — Read governing standards**: For each file type present in the diff, read the governing skill or guide before evaluating.

**Step 3 — Evaluate**: For each changed scaffold file, check compliance against its governing standard. Flag: missing required sections, weak or undifferentiated descriptions, token bloat, incorrect placement, structural violations, typos.

**Step 4 — Report**: Produce a structured report — one entry per file:
- File path
- Governing standard consulted
- Compliance gaps (one line each)
- Disposition: pass / needs revision
