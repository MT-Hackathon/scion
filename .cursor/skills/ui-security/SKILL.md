---
name: ui-security
description: "Governs UI security mandates: credential storage, API key handling, auth token management, XSS prevention, and HTTP/API security boundaries. Use when implementing frontend authentication, token storage, or API authorization headers. DO NOT use for backend security (see security) or RBAC authorization logic (see rbac-authorization)."
---

<ANCHORSKILL-UI-SECURITY>

# UI Security

## Table of Contents & Resources
- [Core Concepts](#core-concepts)
- [Blueprint: API Client Auth](blueprints/api-client-auth.ts)
- [Examples: Credential Handling](resources/examples-credential-handling.md)
- [Examples: Payload Validation](resources/examples-payload-validation.md)
- [Reference: Exposure Rules](resources/reference-exposure-rules.md)
- [Checklist: Security Review](resources/checklist-security-review.md)
- [Cross-References](resources/cross-references.md)

## Core Concepts

### Credential Handling
Keys only in backend vaults. Never persist on client: no localStorage/sessionStorage/disk/JSON/.env. Send via HTTPS, delete with backend call.

### Sensitive Data in Reactive State (FORBIDDEN)
- Never place secrets or PII in shared or long-lived client state (stores, persisted state, caches).
- Secret input values may exist only in shortest-lived local submission scope, must not be copied into shared stores, and must be cleared immediately after submit/cancel.

### Exposure Mitigation
Mask logs (`${key.substring(0,4)}***`), don't show creds in error/console, don't echo secrets from backend, or place in URL params. Test connections show only success/failure.

### Safe URL Construction (MANDATED)
- Never navigate with untrusted input (`window.location.href = userInput`, `window.open(userInput)`).
- Internal navigation uses validated route constants with SvelteKit navigation APIs.
- External URLs must be parsed with `new URL(...)` and checked against an explicit allowlist before navigation.

### Browser API Limits
Use standard fetch/file endpoints or native inputs. No direct disk writes/natives/`window.__TAURI__`.

### Browser API Guardrails (MANDATED)
For browser-only APIs (`window`, `localStorage`, `sessionStorage`, `matchMedia`):
- Guard runtime availability (`typeof window !== 'undefined'`)
- Wrap reads/writes in `try/catch` and fall back safely on failure (SSR/private mode/quota errors)

### HTTP Payload Guards
Validate with Zod before requests, sanitize payloads, reject bodies >1MB, and never use unvalidated raw input directly.

</ANCHORSKILL-UI-SECURITY>
