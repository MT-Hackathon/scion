# Rule Bundling Strategy

Rules can be either single-file or folder-based. Use the appropriate structure based on complexity.

## Single-File Rule (`.mdc`)

Preferred for simple rules with no supporting resources or scripts.

```text
.cursor/rules/
└── {name}.mdc               # Frontmatter: alwaysApply or globs + content
```

Use the [create-rule](@/home/cmb115/.cursor/skills-cursor/create-rule/SKILL.md) skill for these.

## Folder-Based Rule

Required for complex rules that include supporting documentation, checklists, or scripts.

```text
.cursor/rules/{number}-{name}/
├── RULE.mdc               # Activation frontmatter + core mandates
├── resources/             # Supporting documentation
│   ├── checklist-{topic}.md
│   ├── guide-{topic}.md
│   └── reference-{topic}.md
└── scripts/               # Supporting utility scripts
    └── {script}.py
```

### Folder Structure Requirements
- **RULE.mdc**: The entry point. Must contain the activation frontmatter.
- **Resources**: Use mandated prefixes (`checklist-`, `guide-`, `reference-`).
- **Scripts**: Use `uv` for Python scripts and ensure they are non-interactive.

## Why Bundle?
- **Portability**: A bundled folder is easy to transfer between projects using the [transfer workflow](../guide-transfer-workflow.md).
- **Organization**: Keeps `RULE.mdc` lean and narrative-focused while moving details to resources.
- **Maintainability**: Clear separation between core logic and supporting materials.
