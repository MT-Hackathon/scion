# Tag Taxonomy

Knowledge curation and distribution system for shared `.cursor` AI development environments.

## Universal Labels

Most categories use `namespace::value` format. Priority labels use `P{N}-{name}` prefix format for sort-order stability (GitLab sorts alphabetically; `::` namespacing would break rank order).

**Type** (required on every issue):
- `type::feature` — New capability
- `type::enhancement` — Improvement to existing capability
- `type::bug` — Defect in existing capability
- `type::chore` — Maintenance, refactoring with no user-facing change
- `type::spike` — Time-boxed investigation to reduce uncertainty

> **Note**: `gap` was rejected because it overlaps with bug, feature, and spike. Use `spike` for "discover what's missing."

**Priority** (assigned during triage):
- `P0-critical`, `P1-high`, `P2-medium`, `P3-low`
- Prefixed with P-number for sort order

**Layer** (optional, for cross-layer tracking):
- `layer::backend`, `layer::frontend`, `layer::infra`, `layer::docs`
- `layer::contract` — API boundary/contract definitions

**Status** (exception statuses only — board columns own workflow):
- `status::blocked` — External dependency prevents progress
- `status::needs-info` — Waiting on stakeholder clarification
- **Note**: `status::ready` was rejected as it duplicates board columns.

## Project-Specific Labels
Defined per-project in rule 001. Examples for Rootstock:

- **Epics**: `epic::curation-pipeline`, `epic::graft-distribution`, `epic::web-app`, `epic::duo-integration`, `epic::quality-infra`, `epic::accelerator`
- **Domains**: `domain::sync-engine`, `domain::policy`, `domain::curator`, `domain::graft-cli`, `domain::graft-web`

## Required Labels at Creation
1. One `type::` label
2. One `epic::` label

All others are applied during triage.

## Anti-Churn Rules
1. **Namespace everything** — prevents collision with GitLab defaults.
2. **Consult before creating** — never create a label without checking this guide first.
3. **Epics are workstreams** — stable for months, not sprints.
4. **Priority is for triage** — set during triage, not intake.
5. **Workflow in columns** — board columns own workflow state.
6. **Signal over noise** — fewer labels with signal beats more labels with noise.

## Enforcement
Use GitLab issue templates with dropdowns for required fields.
