# Reference: Security Hardening

Implementation patterns for the mandates in SKILL.md §5.7.

---

## File Upload Validation

Attachment endpoints MUST validate both content type and file extension. Size-only checks are insufficient.

```java
private static final Set<String> ALLOWED_CONTENT_TYPES = Set.of(
    "application/pdf", "image/png", "image/jpeg", "image/gif",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/csv", "text/plain"
);

private static final Set<String> ALLOWED_EXTENSIONS = Set.of(
    ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".docx", ".xlsx", ".csv", ".txt"
);

public void validateUpload(MultipartFile file) {
    if (!ALLOWED_CONTENT_TYPES.contains(file.getContentType())) {
        throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "File type not allowed");
    }
    String ext = StringUtils.getFilenameExtension(file.getOriginalFilename());
    if (ext == null || !ALLOWED_EXTENSIONS.contains("." + ext.toLowerCase(Locale.ROOT))) {
        throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "File extension not allowed");
    }
}
```

---

## Secure Error Responses

Never leak stack traces or internal details in API responses. Log full detail server-side; return only safe summaries to clients.

```java
// BAD — exposes internals
throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, e.getMessage());

// GOOD — generic client message, detailed server log
log.error("ATTACHMENT_UPLOAD: validation failed, filename={}, reason={}", filename, e.getMessage(), e);
throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "An internal error occurred");
```

The `GlobalExceptionHandler` ([blueprint](../blueprints/global-exception-handler.java)) maps domain exceptions to RFC 7807 Problem Detail responses. All exception-to-response mappings should live there — never inline `ResponseStatusException` for domain failures.

---

## Rate Limiting

Authentication and SCIM provisioning endpoints are brute-force targets. Apply rate limiting at the gateway or filter level using Bucket4j or Spring Cloud Gateway rate limiters.

- Login: ~5 attempts per minute per IP
- Token refresh: ~10 attempts per minute per IP
- Response: `429 Too Many Requests` with `Retry-After` header

---

## Security Headers

Spring Security's `headers()` Lambda DSL configures `X-Content-Type-Options`, `X-Frame-Options`, `HSTS`, and `CSP`. Verify configuration in `SecurityConfig.java` ([blueprint](../blueprints/security-config.java)) when modifying security filter chains. Never disable default headers without documented justification.
