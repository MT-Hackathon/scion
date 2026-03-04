# API Contract Template

Template for defining API contracts between `procurement-web` (frontend) and `procurement-api` (backend).

## Contract File Template

```typescript
/**
 * {Domain} API Contract
 * 
 * Defines the API contract for {domain} operations between frontend and backend.
 * 
 * Base Path: /api/{domain}
 * Authentication: Required (Okta JWT Bearer token)
 */

// =============================================================================
// ENDPOINT METADATA
// =============================================================================

/**
 * Endpoint: {HTTP_METHOD} /api/{domain}/{path}
 * Description: {What this endpoint does}
 * Auth Required: Yes/No
 * Roles: {Required roles if any}
 */

// =============================================================================
// ENUMS
// =============================================================================

export type {Domain}Status = '{VALUE1}' | '{VALUE2}' | '{VALUE3}';

// =============================================================================
// REQUEST TYPES
// =============================================================================

export interface {Action}{Domain}Request {
  /** {Field description} */
  field1: string;
  
  /** {Optional field description} */
  field2?: number;
}

// =============================================================================
// RESPONSE TYPES
// =============================================================================

export interface {Domain}Response {
  /** Unique identifier */
  id: number;
  
  /** {Field description} */
  field1: string;
  
  /** ISO 8601 timestamp */
  createdAt: string;
}

/** Paginated list response */
export interface {Domain}ListResponse {
  items: {Domain}Response[];
  totalCount: number;
  page: number;
  pageSize: number;
}

// =============================================================================
// ERROR TYPES
// =============================================================================

export interface {Domain}ErrorResponse {
  /** HTTP status code */
  status: number;
  
  /** Error code for client handling */
  code: string;
  
  /** Human-readable message */
  message: string;
  
  /** Field-level validation errors */
  fieldErrors?: Record<string, string[]>;
}

/** Standard error codes for this domain */
export type {Domain}ErrorCode = 
  | '{DOMAIN}_NOT_FOUND'
  | '{DOMAIN}_VALIDATION_ERROR'
  | '{DOMAIN}_CONFLICT'
  | '{DOMAIN}_FORBIDDEN';
```

## Real Example: Delegation Contract

Based on the actual `procurement-api` Delegation domain:

```typescript
/**
 * Delegation API Contract
 * 
 * Defines the API contract for delegation operations between frontend and backend.
 * Delegations allow users to grant approval authority to others during absences.
 * 
 * Base Path: /api/delegations
 * Authentication: Required (Okta JWT Bearer token)
 */

// =============================================================================
// ENUMS
// =============================================================================

/** Status of a delegation */
export type DelegationStatus = 'ACTIVE' | 'REVOKED' | 'EXPIRED';

/** Available delegation scopes */
export type DelegationScopeName = 
  | 'REQUISITION_APPROVAL'
  | 'PURCHASE_ORDER_APPROVAL'
  | 'CONTRACT_APPROVAL'
  | 'BUDGET_APPROVAL';

// =============================================================================
// REQUEST TYPES
// =============================================================================

/**
 * POST /api/delegations
 * Create a new delegation
 */
export interface CreateDelegationRequest {
  /** User ID of the person who will act on behalf of the delegator */
  delegateUserId: string;
  
  /** Start date of delegation (ISO 8601) */
  startDate: string;
  
  /** End date of delegation (ISO 8601) */
  endDate: string;
  
  /** Reason for delegation (e.g., "Vacation", "Out of office") */
  reason?: string;
  
  /** Scopes being delegated */
  scopes: DelegationScopeName[];
}

/**
 * GET /api/delegations
 * Query parameters for listing delegations
 */
export interface ListDelegationsParams {
  /** Filter by status */
  status?: DelegationStatus;
  
  /** Filter by delegator user ID */
  delegatorUserId?: string;
  
  /** Filter by delegate user ID */
  delegateUserId?: string;
  
  /** Include expired delegations (default: false) */
  includeExpired?: boolean;
  
  /** Page number (1-based) */
  page?: number;
  
  /** Page size (default: 20, max: 100) */
  pageSize?: number;
}

/**
 * PUT /api/delegations/{id}/revoke
 * Revoke an active delegation
 */
export interface RevokeDelegationRequest {
  /** Reason for revocation */
  reason?: string;
}

// =============================================================================
// RESPONSE TYPES
// =============================================================================

/** Single delegation response */
export interface DelegationResponse {
  /** Unique identifier */
  id: number;
  
  /** User ID of the person delegating authority */
  delegatorUserId: string;
  
  /** Display name of delegator (from user lookup) */
  delegatorName?: string;
  
  /** User ID of the delegate */
  delegateUserId: string;
  
  /** Display name of delegate (from user lookup) */
  delegateName?: string;
  
  /** Start date (ISO 8601) */
  startDate: string;
  
  /** End date (ISO 8601) */
  endDate: string;
  
  /** Current status */
  status: DelegationStatus;
  
  /** Reason for delegation */
  reason: string | null;
  
  /** Delegated scopes */
  scopes: DelegationScopeName[];
  
  /** Creation timestamp (ISO 8601) */
  createdAt: string;
  
  /** User who created the delegation */
  createdBy: string;
}

/** Paginated list of delegations */
export interface DelegationListResponse {
  items: DelegationResponse[];
  totalCount: number;
  page: number;
  pageSize: number;
}

// =============================================================================
// ERROR TYPES
// =============================================================================

export interface DelegationErrorResponse {
  status: number;
  code: DelegationErrorCode;
  message: string;
  fieldErrors?: Record<string, string[]>;
}

export type DelegationErrorCode = 
  | 'DELEGATION_NOT_FOUND'
  | 'DELEGATION_ALREADY_REVOKED'
  | 'DELEGATION_EXPIRED'
  | 'DELEGATION_OVERLAP'        // Cannot create overlapping delegations
  | 'DELEGATION_SELF_DELEGATE'  // Cannot delegate to yourself
  | 'DELEGATION_INVALID_DATES'  // End date before start date
  | 'DELEGATION_FORBIDDEN';     // Not authorized to manage this delegation
```

## Contract Conventions

### Naming

| Element | Convention | Example |
|---------|-----------|---------|
| File | `{domain}.contract.ts` | `delegation.contract.ts` |
| Create request | `Create{Domain}Request` | `CreateDelegationRequest` |
| Update request | `Update{Domain}Request` | `UpdateDelegationRequest` |
| List params | `List{Domain}Params` | `ListDelegationsParams` |
| Single response | `{Domain}Response` | `DelegationResponse` |
| List response | `{Domain}ListResponse` | `DelegationListResponse` |
| Error response | `{Domain}ErrorResponse` | `DelegationErrorResponse` |
| Error codes | `{Domain}ErrorCode` | `DelegationErrorCode` |
| Status enums | `{Domain}Status` | `DelegationStatus` |

### Date/Time

- Always use ISO 8601 strings for dates: `"2025-01-23T10:30:00Z"`
- Backend converts to/from `LocalDateTime` or `Instant`
- Document timezone expectations in JSDoc

### Pagination

Standard pagination response structure:

```typescript
interface PaginatedResponse<T> {
  items: T[];
  totalCount: number;
  page: number;       // 1-based
  pageSize: number;
}
```

### Optional Fields

- Use `?` for optional request fields
- Use `| null` for nullable response fields
- Document defaults in JSDoc comments

### Error Codes

- Use SCREAMING_SNAKE_CASE
- Prefix with domain name
- Be specific enough for frontend error handling

## Cross-References

- [guide-cross-repo-implementation.md](guide-cross-repo-implementation.md) - Unified implementation guide
- [checklist-api-implementation.md](checklist-api-implementation.md) - Implementation checklist
- [reference-api-endpoints.md](reference-api-endpoints.md) - Existing endpoints
