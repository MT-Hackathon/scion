# Cross-Repository Task Checklist

Pre-flight validation before initiating cross-repo implementation between `procurement-web` and `procurement-api`.

## Before Defining Contract

- [ ] **Confirmed endpoint doesn't exist** - Checked `reference-api-endpoints.md` and backend repo
- [ ] **Identified the domain** - Know which entity/feature area this belongs to
- [ ] **Understood the user workflow** - Can describe how user will interact with this feature
- [ ] **Identified consuming component** - Know which Angular component(s) need this data

## Contract Definition

- [ ] **Request type defined** - All required fields documented with types
- [ ] **Response type defined** - All returned fields documented with types
- [ ] **Error types defined** - Error codes and response structure specified
- [ ] **Pagination included** (if list endpoint) - Standard pagination response structure
- [ ] **Dates use ISO 8601** - All date/time fields documented as strings

## Contract Quality

- [ ] **Types are precise** - No `any`, minimal `unknown`, specific unions where applicable
- [ ] **Optional vs required clear** - `?` for optional, `| null` for nullable
- [ ] **Field descriptions present** - JSDoc comments explain each field's purpose
- [ ] **Error codes are specific** - Each error condition has a unique code
- [ ] **Default values documented** - Optional params document their defaults

## Implementation Preparation

- [ ] **Endpoint path specified** - Full path including `/api/` prefix
- [ ] **HTTP method specified** - GET, POST, PUT, DELETE, PATCH
- [ ] **Auth requirements documented** - Required roles or "any authenticated"
- [ ] **Business rules documented** - Validation and logic requirements
- [ ] **Testing expectations set** - What tests to write (unit/integration)

## Implementation Checklist

- [ ] **Context established** - Frontend need, user workflow, component identified
- [ ] **Contract generated** - Full TypeScript interfaces available
- [ ] **Error cases listed** - Condition, error code, HTTP status for each
- [ ] **Implementation plan complete** - Step-by-step plan for both repos

## Post-Implementation

- [ ] **Backend verified** - Tests written and passing in `procurement-api/`
- [ ] **Endpoint added to reference** - Updated `reference-api-endpoints.md`
- [ ] **Frontend service integrated** - Angular service method using real API
- [ ] **Frontend verified** - Tests verify service calls and UI behavior

## Quick Reference: Common Issues

| Issue | Prevention |
|-------|------------|
| Contract mismatch | Use TypeScript types, not just descriptions |
| Missing error handling | Define all error codes upfront |
| Pagination forgotten | Always include for list endpoints |
| Auth assumptions | Explicitly document auth requirements |
| Date format confusion | Always specify ISO 8601 in JSDoc |

## Cross-References

- [guide-cross-repo-implementation.md](guide-cross-repo-implementation.md) - Full guide
- [template-api-contract.md](template-api-contract.md) - Contract template
- [checklist-api-implementation.md](checklist-api-implementation.md) - Implementation checklist
- [reference-api-endpoints.md](reference-api-endpoints.md) - Existing endpoints
