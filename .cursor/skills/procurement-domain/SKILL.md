---
name: procurement-domain
description: "Provides Montana procurement system domain knowledge: workflow lifecycle, approval gates, agency model, roles, and system states. Use when working on workflow, routing, approval, agency, or request-handling code. DO NOT use for product management process (see product-management) or security implementation (see security)."
---

<ANCHORSKILL-PROCUREMENT-DOMAIN>

# Procurement Domain

Domain knowledge for the Montana State procurement intake and approval system.

## When to Use This Skill

- Working on workflow, routing, approval, or request-handling code
- Implementing or modifying approval gates
- Debugging routing logic or status transitions
- Working with agency-related entities (originating vs purchasing agency)
- Implementing display name patterns
- Understanding role permissions or queue behavior
- Designing new features that touch the procurement lifecycle

## Quick Reference

### Two-Stage Lifecycle
1. **Intake/Refine**: Requester draft → APO elevates to Procurement Request
2. **Approval/Routing**: Parallel gates → Authority check → Handoff to eProcurement

### Parallel Approval Gates
| Gate | Trigger | Type |
|------|---------|------|
| Agency Chain | Always | Position-based roles (configurable per-agency) |
| IT Review | IT purchase category | Hard gate, parallel with agency |
| Strategic Sourcing | Cooperative Buy | First stop, checks existing contracts |
| OBPP | $200K+ | Budget office approval |
| Central Procurement | Exceeds authority OR Sole Source | Final authority |

### Two Orthogonal Dimensions
- **What (Purchase Type)**: IT, Commodity, Other. Triggers gates (e.g., IT Review).
- **How (Procurement Method)**: Sole Source, Coop, RFP, IFB. Determines workflow routing.

### Assignment Paradigms
- **Queue (Pull)**: Team views items, self-assign primary, supervisor can assign
- **Approval (Push)**: System routes based on chain position, notification sent

### Key Principles
- **Agency Sovereignty**: Purchasing agency controls the approval chain (their budget, their call)
- **APO as Funnel**: All "more info" requests route through APO, chain resets
- **Delegated Authority**: Configuration table, not per-request calculation (rules engine evaluates)
- **Description vs. Justification**: `description` = what we're buying; `justification` = why we're buying it this way. Not interchangeable.
- **Audit**: Every field change + milestones, who acted (not viewed)

### Display Name Architecture
All domain display names (statuses, roles, categories) are server-driven via `/api/v1/config`.
- **Backend**: `DisplayNameRegistry` centralizes maps with `resolve(domain, code)`
- **Frontend**: `DisplayNameRegistry` service reads from cached config signal; `DisplayNamePipe` for templates
- **Unified Shape**: `LabeledValue` atom `{ code: string, displayName: string }` for all domain labels
- **Fallback chain**: Server value → `humanize(code)` → Raw code (defense-in-depth, never blank)

### Key File Locations

| Component | Backend (relative to `src/main/java/doa/procurement/workflow/`) | Frontend (relative to `src/app/`) |
|-----------|---------|----------|
| API Contract | `<domain>/dto/` + Springdoc annotations on controllers | Hand-written feature models (`features/**/models/`) |
| Security | `config/SecurityConfig.java` | `core/interceptor/` |
| Identity | `identity/IdentityService.java` | `services/identity-validation.service.ts` |
| Rules | `rules/RulesService.java` | `features/rules-engine/` |
| Requests | `request/Request.java` | `features/intake/` |
| Display Names | `config/DisplayNameRegistry.java` | `core/configuration/display-name-registry.service.ts` |

## Resources

- Procurement Workflow Mental Model (`docs/procurement-workflow-mental-model.md` in the target project) — **Primary resource**: Full lifecycle, gates, agency sovereignty, roles, system states, and Mermaid visualization. This file lives in the deployed project, not in rootstock.

## Cross-References

- [Rootstock System Rule](../../rules/005-rootstock-system/RULE.mdc) — Always-on safety invariants
- [Security Skill](../security/SKILL.md) — Identity flow, auth chain, provisioning gate details
- [Product Management Skill](../product-management/SKILL.md) — Feature governance, checklists, acceptance criteria

</ANCHORSKILL-PROCUREMENT-DOMAIN>
