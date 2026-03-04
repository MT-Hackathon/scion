---
name: security
description: "Governs credential security, API authentication, JWT/OAuth patterns, and .env management. Use when implementing authentication flows, managing secrets, configuring security layers, or handling multi-role (X-Active-Role) session boundaries. DO NOT use for UI-layer security (see ui-security) or RBAC authorization logic (see rbac-authorization)."
---

<ANCHORSKILL-SECURITY>

# Security

## Credential & Authorization Baseline (MANDATORY)

### Credential Storage
- Secrets (API keys, passwords, tokens) must be stored in environment variables or managed secret stores.
- Development uses `.env` with `python-dotenv`; `.env` stays gitignored and `.env.example` is committed.
- Production uses managed secret stores (AWS/Azure/etc.) with required-key validation at startup.

### Authentication Types
Use only explicit auth patterns:

```python
# Header auth (api_key)
headers["Authorization"] = f"Bearer {credentials_ref}"

# Query auth (api_key_query)
params["appid"] = credentials_ref
```

### Authorization Verification Mode (FAIL-CLOSED)
- If authorization evaluation is indeterminate (missing context, dependency outage, policy evaluation error), deny by default and return HTTP 500.
- Return HTTP 403 only when authorization evaluation completes successfully and explicitly denies access.
- Never allow access when authorization state is indeterminate.

### Credential Exposure Prevention
- Never log, print, or return raw credential values.
- Redact secrets in logs (`prefix***` style).
- Error messages must not include secrets or connection strings.

### Connection Security
- Enforce TLS >= 1.2 for outbound API/database connections.
- Never disable certificate verification outside isolated local test code.

### Prohibited Patterns
- Hardcoded credentials in code, tests, or config.
- Storing secrets in JSON/YAML or committed `.env` files.
- Plain HTTP on production data paths.
- Persisting secrets in DataFrames or user-visible payloads.

## Authorization Mandates (Stack-Agnostic)

### Typed Denial
Use enums (not booleans) for security outcomes with multiple denial reasons. A boolean collapses "not found" into "allowed" — the distinction is invisible to ops logging and audit.

### Dev-Only Override Headers
Override mechanisms (e.g., `X-Override-Role`, debug bypass flags) must be gated at the server boundary to non-production environments. Production MUST reject them unconditionally — documentation saying "don't use in production" is not enforcement.

### Session Boundary Cleanup
Permission caches, role context, and derived auth state must be cleared on every session boundary (login, logout, role switch, session expiry). Stale auth state from a prior session is an authorization bypass.

### User Identity Normalization
Normalize user identifiers (email, user ID) to a canonical form (typically lowercase) at the trust boundary — the point where an external token is first processed. Downstream comparisons that assume normalization without enforcing it at the boundary produce silent auth failures.

## Source Pointers

| Pattern | Location |
|---|---|
| API client auth (SSR guard, timeout, Bearer token injection) | [`ui-security/blueprints/api-client-auth.ts`](../ui-security/blueprints/api-client-auth.ts) |
| Python env-var loading and header auth | [`resources/reference-auth-patterns.md`](resources/reference-auth-patterns.md) |

## Resources
- [Reference: Auth Patterns](resources/reference-auth-patterns.md)
- [Reference: RBAC Patterns](resources/reference-rbac-patterns.md)
- [Examples: Audit Logging](resources/examples-audit-logging.md)
- [Checklist: Credential Security](resources/checklist-credential-security.md)
- [Checklist: Security Audit](resources/checklist-security-audit.md)

</ANCHORSKILL-SECURITY>
