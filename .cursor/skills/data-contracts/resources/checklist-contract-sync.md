# Checklist: Contract Synchronization

Data contract validation and sync checklist.

---

## Schema Definition

- [ ] All schemas documented in `data-contracts-context.md`
- [ ] Schema fields match exactly between frontend and backend
- [ ] Validation rules identical on both sides
- [ ] Required/optional fields match
- [ ] Default values match
- [ ] Enum values match exactly (same strings/ordering)

## Frontend Validation (Zod)

- [ ] Zod schemas defined for all data contracts
- [ ] Validation at form submit
- [ ] Validation before API calls
- [ ] Inline errors displayed to user
- [ ] Error messages are actionable
- [ ] TypeScript types inferred from Zod schemas

## Backend Validation (Pydantic)

- [ ] Pydantic models defined for all data contracts
- [ ] Validation on `execute_pipeline` entry point
- [ ] Invalid config rejected with `INVALID_CONFIG` error code
- [ ] Validation errors include field details
- [ ] No untrusted config used without validation

## Sync Process

- [ ] `data-contracts-context.md` updated first (source of truth)
- [ ] Frontend Zod schema updated
- [ ] Backend Pydantic model updated
- [ ] Both schemas tested with same test cases
- [ ] API types updated if needed
- [ ] Documentation updated

## Testing

- [ ] Valid configs pass on both frontend and backend
- [ ] Invalid configs fail on both frontend and backend
- [ ] Same test fixtures used for both sides
- [ ] Edge cases tested (empty strings, null, undefined)
- [ ] Type coercion tested (string to number, etc.)

## Prohibited Patterns

- [ ] No schema divergence between frontend/backend
- [ ] No different validation rules
- [ ] No runtime modification without re-validation
- [ ] No missing validation for user input
- [ ] No trusting config without validation
- [ ] No skipping documentation updates

## Contract Template

- [ ] Field name matches across frontend/backend
- [ ] Type mapping correct (string ↔ str, number ↔ int)
- [ ] Validation rules match exactly
- [ ] Required/optional status matches
- [ ] Default values match
