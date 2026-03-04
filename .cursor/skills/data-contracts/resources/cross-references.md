# Cross-References: Data Contracts

Related skills/rules and anchors.

---

## Related Skills/Rules
- [fullstack-workflow](../../fullstack-workflow/SKILL.md): Type sync procedures
- [data-mapping](../../data-mapping/SKILL.md): Backend ECS mapping
- [svelte-ui](../../svelte-ui/SKILL.md): Frontend form validation patterns

## Defined Anchors
- `ANCHORSKILL-DATA-CONTRACTS`: Data contract validation mandate

## Referenced Anchors
- `ANCHORCONTEXT-DATA-CONTRACTS`: All schema specifications (context file)
- `ANCHORSKILL-FULLSTACK-WORKFLOW`: Type sync procedures (fullstack-workflow)
- `ANCHORSKILL-DATA-MAPPING`: Backend mapping (data-mapping)
- `ANCHORSKILL-SVELTE-UI`: Frontend validation (svelte-ui)

## Key Files (project-relative conventions)
- `.cursor/context/data-contracts-context.md`: Schema source of truth (project-level context file)
- Frontend Zod schemas: location varies by project (e.g. `app/frontend/src/lib/schemas/`)
- Backend Pydantic models: location varies by project (e.g. `app/backend/src/graft/models.py`)

## Validation Flow
1. **Frontend:** Form submit → Zod validation → Inline errors
2. **Frontend:** Before API call → Re-validate → Send
3. **Backend:** Receive → Pydantic validation → Execute or reject
4. **Both:** Same data must pass/fail identically
