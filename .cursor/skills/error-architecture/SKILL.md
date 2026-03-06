---
name: error-architecture
description: "Governs error architecture and handling mandates across all layers: exception modeling, HTTP error responses, global handlers, and error propagation patterns. Use when implementing error handling, defining error response contracts, or debugging error flows. DO NOT use for debugging test failures (see testing-debugging) or UI error display (see svelte-ui)."
---

<ANCHORSKILL-ERROR-ARCHITECTURE>

# Error Architecture Rule

## Table of Contents & Resources
- [Core Concepts](#core-concepts)
- [Blueprint: Error Hierarchy](blueprints/error-hierarchy.py)
- [Examples: Error Mapping](resources/examples-error-mapping.md)
- [Checklist: Error Handling](resources/checklist-error-handling.md)
- [Cross-References](resources/cross-references.md)

## Core Concepts

### Error Codes (MANDATED)
`CONNECTION_FAILED`, `INVALID_CONFIG`, `TIMEOUT`, `UNAUTHORIZED`, `PIPELINE_ERROR`, `VALIDATION_ERROR`, `RESOURCE_NOT_FOUND`, `RATE_LIMIT_EXCEEDED`, `UNKNOWN_ERROR`

### Error Response (MANDATED)
**Required:** `status: "error"`, `error` (message), `code` (from above)  
**Optional:** `details`, `id`  
**All layers preserve this envelope unchanged**

### Layer Responsibilities
- **Backend:** Map exceptions → codes, log once (no stack traces in output), guard clauses
- **HTTP/API:** Forward unchanged, 30s timeout
- **Frontend:** Display by severity (toast/inline/modal/indicator), show message only

### User-Facing Error Mapping (MANDATED)
- Map backend `error.code` to user-friendly messages; if `error.code` is missing, map by HTTP status.
- Never display raw backend payloads, exception text, or stack traces in UI.
- Minimum fallback mapping: `401` session/auth required, `403` permission denied, `404` not found, `429` retry later, `5xx` generic failure.

### Structured Logging (MANDATED)
- Use domain-action prefixes for significant transitions and failures: `DOMAIN_ACTION: key=value ...`.
- Include stable identifiers (`request_id`, `entity_id`, `user_id`) and never log secrets.
- Emit each error once at the handling boundary to avoid duplicate noise across layers.

### Message Quality
Specific, actionable, concise; no stack traces, internals, or credentials

### Testing
Assert `status`/`error`/`code` presence; verify backend → IPC → frontend propagation

### HTTP Error Mapping Pattern
Build RFC 7807-style detail envelopes `{title, detail, status}` as HTTP exceptions. Use a typed catch pattern that maps domain errors to status codes (e.g., config/validation errors → 400, auth errors → 401/403, infrastructure errors → 500). Maintain a constants module for mandated error title strings to ensure consistency across handlers.

</ANCHORSKILL-ERROR-ARCHITECTURE>
