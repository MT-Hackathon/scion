# Cross-References: UI Canvas

Related skills and anchors.

---

## Related Skills

- [svelte-ui](../svelte-ui/SKILL.md): Component patterns, token system, debugging workflow, forms and validation (for node configuration forms)
- [ui-security](../ui-security/SKILL.md): Credential handling in node configurations
- [data-contracts](../data-contracts/SKILL.md): Schema validation for pipeline configs

## Defined Anchors

- `ANCHORSKILL-UI-CANVAS`: Canvas and pipeline patterns (in `SKILL.md`)

## Key Principles

- **Node Types:** Source (green/out), Transform (purple/bidirectional), Target (blue/in)
- **Tokens:** All visuals from `--node-*` tokens, never hardcoded
- **Edge Validation:** On-drop validation, no circular deps or self-loops
- **Configuration:** Zod validation, Semver versioning, `.pipeline.json` extension
- **Auto-Save:** Every 30s, 5MB limit, prompt before load
