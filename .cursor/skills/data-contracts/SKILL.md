---
name: data-contracts
description: "Governs data contract validation mandates and type synchronization requirements across API boundaries. Use when validating schema compatibility, syncing TypeScript types with backend DTOs, or enforcing contract rules at the API boundary. DO NOT use for PostgreSQL schema design (see postgresql-design) or API annotation authoring (see api-design)."
---

<ANCHORSKILL-DATA-CONTRACTS>

# Data Contracts Rule

## Table of Contents & Resources
- [Core Concepts](#core-concepts)
- [Blueprint: Zod Contract](blueprints/zod-contract.ts)
- [Blueprint: Pydantic Contract](blueprints/pydantic-contract.py)
- [Examples: Dual Validation](resources/examples-dual-validation.md)
- [Examples: Contract Sync](resources/examples-contract-sync.md)
- [Examples: Shared Fixtures](resources/examples-shared-fixtures.md)
- [Checklist: Contract Sync](resources/checklist-contract-sync.md)
- [Cross-References](resources/cross-references.md)

## Core Concepts

### Schema Location
All schemas defined in `data-contracts-context.md`

### Validation (MANDATED)
**Frontend:** Zod, validate at form submit + before API call, inline errors  
**Backend:** Pydantic, validate on `execute_pipeline`, reject with `INVALID_CONFIG`  
**Contract:** Same data must pass/fail both sides

### Sync Process
1. Update `data-contracts-context.md` (source of truth)
2. Update Zod + Pydantic
3. Run tests
4. Update API types if needed

### Prohibited
Schema divergence, validation differences, runtime modification without re-validation, missing validation for user input, untrusted config

</ANCHORSKILL-DATA-CONTRACTS>
