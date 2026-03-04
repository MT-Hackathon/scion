# Skill Quality Checklist

Use this checklist when curating a skill. Mark each item pass or fail with brief evidence.

## 1) Description Quality

- [ ] Frontmatter `name` is <= 64 chars and uses lowercase hyphens only.
- [ ] Description is third-person ("Provides", "Governs", "Implements").
- [ ] Description includes high-probability trigger keywords for the domain.
- [ ] Description includes explicit "Use when / DO NOT use" delineation.
- [ ] Description is concise (target around 50 tokens; not vague or bloated).

## 2) Folder Structure Fit

- [ ] Skill uses canonical structure intent: `SKILL.md`, `resources/`, optional `blueprints/`, optional `scripts/`.
- [ ] Placement is justified by content type (governance in `SKILL.md`, narration in `resources/`).
- [ ] `blueprints/` exists when recurring structural scaffolding is needed.
- [ ] `scripts/` exists only when repeatable execution beats prose instructions.

## 3) Body Budget and Navigation

- [ ] `SKILL.md` is <= 500 lines.
- [ ] Table of Contents is present when `SKILL.md` is 100+ lines.
- [ ] Anchor tag exists for targeted reading.
- [ ] Core file stays governance-focused; long details moved to `resources/`.

## 4) Blueprint Quality (if blueprints exist)

- [ ] Files in `blueprints/` are real code files (not markdown pseudo-code).
- [ ] Each blueprint is 20-100 lines.
- [ ] Header includes `BLUEPRINT`, `STRUCTURAL`, and `ILLUSTRATIVE` comments.
- [ ] Structural elements are reusable; illustrative elements are clearly replaceable.

## 5) Cross-Reference Quality

- [ ] Cross-references are present for adjacent skills or related governance.
- [ ] All links use relative paths (no machine-local absolute paths).
- [ ] Links resolve to existing files (no broken references).

## 6) Script Quality (if scripts exist)

- [ ] Python scripts use PEP 723 inline metadata when dependencies are required.
- [ ] Scripts are runnable with `uv run --script`.
- [ ] Scripts are non-interactive (flags/args, no prompts).
- [ ] Output is structured when automation consumers are expected.
