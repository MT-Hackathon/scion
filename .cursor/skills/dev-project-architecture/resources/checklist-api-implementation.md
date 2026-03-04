# API Implementation Checklist

Unified checklist for implementing an API that spans both `procurement-web` (frontend) and `procurement-api` (backend).

## Contract Definition

Use this structure to define the API requirements before implementation.

### Context
- **Frontend Need**: {Brief description}
- **User Workflow**: {How the user interacts with this}
- **Frontend Component**: {Consuming component path}

### Endpoint Details
| Property | Value |
|----------|-------|
| Path | `/api/{path}` |
| Method | `{GET/POST/PUT/DELETE}` |
| Auth Required | Yes |
| Required Roles | {Roles} |

### Schema (TypeScript)
```typescript
// Paste or define the request/response types
```

## Implementation Checklist

### 1. Preparation (Backend Contract)
- [ ] Create/update DTO record with `@Schema` and Bean Validation annotations in `procurement-api/src/main/java/doa/procurement/workflow/<domain>/dto/`
- [ ] Add/update controller endpoint with `@Operation`, `@ApiResponse`, and `@Tag`
- [ ] Ensure `@RequestBody` parameters include `@Valid`
- [ ] Verify generated contract at `/v3/api-docs`

### 2. Backend Implementation (`procurement-api/`)
- [ ] Implement Controller with correct path and method
- [ ] Implement Service logic and validations
- [ ] Implement Repository queries
- [ ] Add JavaDoc to public methods

### 3. Backend Verification
- [ ] Unit tests for Service layer (`*ServiceTest.java`)
- [ ] Integration tests for Controller (`*ControllerTest.java`)
- [ ] Verify error codes match contract (400, 401, 403, 404, 409)
- [ ] Run `./gradlew test`

### 4. Frontend Integration (`procurement-web/`)
- [ ] Replace mocks in Angular Service with real `HttpClient` calls
- [ ] Update components to handle loading/error states
- [ ] Verify hand-written feature models in `src/app/features/**/models/` and forms match backend DTO/controller responses

### 5. Final Verification
- [ ] Run frontend tests (`npm test`)
- [ ] Verify end-to-end flow in browser if applicable
- [ ] Update `reference-api-endpoints.md`

---

## Reference Example: Create Delegation

### Context
- **Frontend Need**: Allow managers to create delegations.
- **User Workflow**: Manager fills form on "Create Delegation" page and submits.
- **Frontend Component**: `procurement-web/src/app/features/delegation/delegation-form.component.ts`

### Schema
```typescript
export interface CreateDelegationRequest {
  delegateUserId: string;
  startDate: string;  // ISO 8601
  endDate: string;    // ISO 8601
  reason?: string;
  scopes: DelegationScopeName[];
}

export interface DelegationResponse {
  id: number;
  delegatorUserId: string;
  delegateUserId: string;
  status: 'ACTIVE' | 'REVOKED' | 'EXPIRED';
  // ...
}
```

### Implementation Requirements
- **Validation**: `endDate` must be after `startDate`; `delegateUserId` must exist.
- **Business Logic**: Check for overlapping active delegations; prevent self-delegation.
- **Error Cases**: 
  - `DELEGATION_OVERLAP` (409)
  - `DELEGATION_SELF_DELEGATE` (400)
  - `DELEGATION_INVALID_DATES` (400)
