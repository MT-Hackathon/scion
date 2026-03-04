# Checklist: Configuration Save/Load

Configuration persistence validation checklist.

---

## Schema Definition

- [ ] Using Zod for config validation
- [ ] Schema includes `version`, `nodes`, `edges`, `metadata`
- [ ] Node schema validates `id`, `type`, `position`, `data`
- [ ] Edge schema validates `id`, `source`, `target`
- [ ] Metadata includes `name`, `created`, `modified`
- [ ] Schema checks for duplicate node/edge IDs
- [ ] Schema validates Semver version format

## Save Operations

- [ ] Config validated with Zod before saving
- [ ] Validation errors shown to user
- [ ] Save to backend uses POST `/api/pipelines`
- [ ] Download uses `.pipeline.json` extension
- [ ] JSON formatted with pretty printing (indent 2)
- [ ] User can choose save location (backend vs download)

## Load Operations

- [ ] Load from file uses native file input
- [ ] Load from backend uses GET `/api/pipelines/{id}`
- [ ] File input accepts `.pipeline.json` or `.json`
- [ ] Loaded config validated with Zod
- [ ] Invalid configs show error to user (not silent failure)
- [ ] Validated config applied to canvas

## Version Migration

- [ ] Version field uses Semver format (`1.0.0`)
- [ ] Old versions auto-migrated on load
- [ ] Migration logic for each supported old version
- [ ] Unsupported versions show error
- [ ] Current version clearly documented

## Auto-Save

- [ ] Auto-save runs every 30 seconds
- [ ] Auto-save to localStorage or backend draft
- [ ] Auto-save size limited to 5MB
- [ ] Auto-save cleared on manual save
- [ ] User prompted before loading auto-saved config
- [ ] Auto-save interval cleared on component unmount

## Settings Separation

- [ ] Pipeline configs don't include theme/layout settings
- [ ] Visual settings use `settingsStore.ts` (not pipeline config)
- [ ] Pipeline config only includes node/edge data
- [ ] No mixing of user preferences with pipeline structure

## Prohibited Patterns

- [ ] No silent overwrites (always prompt user)
- [ ] No auto-save without confirmation on load
- [ ] No saving invalid configs
- [ ] No mixing settings with pipeline data
- [ ] No hardcoded versions in multiple places
