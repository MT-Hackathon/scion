---
name: java-spring-boot
description: "Governs Java Spring Boot patterns for REST APIs: facade-based service decomposition, JPA entity mapping, repository patterns, Spring MVC controllers, and Hibernate query optimization. Use when implementing Spring services, JPA entities, REST endpoints, or Gradle builds. DO NOT use for API schema design (see api-design) or database schema design (see postgresql-design)."
---

<ANCHORSKILL-JAVA-SPRING-BOOT>

# Java Spring Boot

## 1. Stack & Standards
- **Java 25** (Sequenced Collections, `RestClient`)
- **Spring Boot 4.0.2** (Jackson 3.x, Spring Security 7)
- **DSL**: Spring Security uses Lambda DSL exclusively.
- **Jakarta**: Use `jakarta.*` imports (not `javax.*`).

## 2. Service Decomposition (Facade Pattern)
Mandatory when a service exceeds **400 lines**:
- **Facade**: Thin service class for public API and `@Transactional`.
- **Domain Services**: Logic moved to focused `{Domain}DomainService.java` files.
- **Orchestration**: Facade calls domain services; contains no core logic.

## 3. Performance: N+1 Prevention
- **Queries**: Use `JOIN FETCH` for relationships accessed in the same transaction.
- **Filtering**: Always filter in the database (`@Query`), never in-memory.
- **FK Indexing**: Mandatory indices for all Foreign Key columns (manually in migration).

## 4. Jackson 3.x Immutability
- **ObjectMapper**: Immutable; use `JsonMapper.builder().build()`.
- **Package**: `tools.jackson.*` (not `com.fasterxml.jackson.*`).

## 5. Security & Identity
- **Normalization**: User IDs MUST be lowercased via `toLowerCase(Locale.ROOT)`.
- **Authorization**: Every `@RestController` method requires `@PreAuthorize`.
- **Active Role**: Access permissions via `X-Active-Role` context (see [Security Skill](../security/SKILL.md)).
- **Fail-Closed Optionals**: In auth paths, `Optional.empty()` must never be treated as success. `.orElseThrow(...)` is for system invariants (entity MUST exist for correctness). For business lookups where "not found" is valid, return `Optional<T>` or a result record.
- **Typed Status over Boolean**: When a check has multiple business outcomes (`NOT_PROVISIONED`, `DEACTIVATED`, `REVOKED`), return a record with a status enum and branch explicitly in the controller/caller. Boolean collapses failure modes.

## 5.5 Null Safety & Validation
- **Equals**: `Objects.equals(a, b)` — never `a.equals(b)` when `a` can be null.
- **Enum Comparison**: Use `==` for enum identity. Never `.equals()` on enums.
- **Validation**: `@Valid` on every `@RequestBody`. Generated models carry `@NotNull` from OpenAPI specs. Exception: generated API interface implementations — configure `@Valid` at the generator level.
- **Exception Narrowing**: Catch specific types (`DataAccessException`, `JacksonException`), never `Exception`. Document best-effort patterns with comments.
- **Verification**: `./gradlew checkstyleMain spotbugsMain` before committing Java changes.

## 5.7 Security Hardening

**File Upload Validation**: Attachment endpoints MUST validate both content type and file extension against an allowlist. Size-only checks are insufficient.

**Secure Error Responses**: Never leak stack traces or internal details in API responses. The `GlobalExceptionHandler` maps exceptions to RFC 7807 Problem Detail responses with generic messages. Log full details server-side; return only safe summaries to clients.

**Rate Limiting**: Authentication and SCIM provisioning endpoints are brute-force targets. Apply at gateway or filter level (Bucket4j / Spring Cloud Gateway). Targets: ~5 login attempts/min per IP, ~10 token refreshes/min per IP. Return `429 Too Many Requests` with `Retry-After`.

**Security Headers**: Spring Security's `headers()` Lambda DSL configures `X-Content-Type-Options`, `X-Frame-Options`, `HSTS`, `CSP`. Verify in `SecurityConfig.java` when modifying filter chains. Never disable default headers without documented justification.

→ Implementation patterns and code examples: [Reference: Security Hardening](resources/reference-security-hardening.md)

## 6. Investigation & Telemetry
- **Structured Logs**: `log.warn("DOMAIN_ACTION: reason={}, field={}", reason, value)`.
- **Trace Context**: Every error includes a `traceId` for correlation.
- **Actuator**: Change log levels at runtime via `/actuator/loggers`.

## 7. Resources

**Examples**
- [Service Patterns](resources/examples-service-patterns.md)
- [Repository Patterns](resources/examples-repository-patterns.md)
- [Controller Patterns](resources/examples-controller-patterns.md)
- [Testing Patterns](resources/examples-testing-patterns.md)

**References**
- [Security Hardening](resources/reference-security-hardening.md)
- [Lombok Patterns](resources/reference-lombok-patterns.md)
- [Java 25 Features](resources/reference-java-25-features.md)
- [Cross-References](resources/cross-references.md)

**Blueprints**
- [SecurityConfig](blueprints/security-config.java)
- [GlobalExceptionHandler](blueprints/global-exception-handler.java)

</ANCHORSKILL-JAVA-SPRING-BOOT>
