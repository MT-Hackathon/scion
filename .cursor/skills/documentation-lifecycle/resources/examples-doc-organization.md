# Examples: Documentation Organization

Documentation organization patterns for procurement-web.

---

## Correct Locations

| Document Type | Correct Location | Example |
|---------------|------------------|---------|
| Feature plans | `.cursor/plans/` | `.cursor/plans/auth-implementation-plan.md` |
| Test reports | `docs/test-reports/` | `docs/test-reports/2025-12-30-integration-results.md` |
| Implementation docs | `docs/implementations/` | `docs/implementations/okta-auth-setup.md` |
| ADRs | `docs/adr/` | `docs/adr/0001-use-angular-signals.md` |

## Anti-Patterns (Root Clutter)

- `./implementation-notes.md`
- `./TODO.md`
- `./CHANGELOG.md` (use git tags instead)
- `./notes/` directory

## Naming Patterns

### Time-Sensitive Documents

```
YYYY-MM-DD-{description}.md
```

- `2025-12-30-security-audit.md`
- `2026-01-13-performance-baseline.md`

### Persistent Documents

```
{topic}-{specificity}.md
```

- `api-contract-v1.md`
- `component-patterns.md`
- `accessibility-checklist.md`

### ADR Numbering

```
{nnnn}-{decision-topic}.md
```

- `0001-use-angular-signals.md`
- `0002-vitest-over-jasmine.md`
- `0003-okta-authentication.md`

## Quarterly Pruning Workflow

1. Review `.cursor/plans/` — archive completed plans older than 90 days
2. Review `docs/test-reports/` — delete reports older than 90 days
3. Review `docs/implementations/` — mark superseded docs as `[DEPRECATED]`
