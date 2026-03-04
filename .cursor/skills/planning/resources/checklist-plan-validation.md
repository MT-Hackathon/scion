# Checklist: Planning Requirements

Pre-submission validation for all plans.

---

## Plan Structure Checklist
- [ ] Every file path includes line range
- [ ] Every code change has before/after snippets
- [ ] Verification command provided for each step
- [ ] No vague language (consider, maybe, TBD, ?)
- [ ] Steps are appropriately sized

## Test Quality Checklist
- [ ] Tests validate behavior (not just types)
- [ ] State delta verification present (initial → action → expected)
- [ ] None/empty/boundary tests explicitly listed
- [ ] Guard clause tests included with failing inputs
- [ ] No try-except masking errors
- [ ] No magic numbers in test data

## Prerequisite Checklist
- [ ] Auth/secrets: KEK env vars verified
- [ ] External APIs: Existing scripts checked
- [ ] Test environment requirements known
