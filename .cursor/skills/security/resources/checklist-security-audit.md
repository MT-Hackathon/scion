# Checklist: Security Audit

Systematic security review for Angular 21 + Spring Boot 4 web applications with PostgreSQL.

---

## Audit Workflow

Copy this checklist and work through each category:

```
Security Audit Progress:
- [ ] 1. Authentication & Session Management
- [ ] 2. Authorization & Access Control
- [ ] 3. Input Validation & Injection
- [ ] 4. API Security
- [ ] 5. Data Protection & Secrets
- [ ] 6. Frontend Security
- [ ] 7. File Upload Security
- [ ] 8. Infrastructure & Docker
- [ ] 9. Dependencies
- [ ] 10. Logging & Monitoring
```

---

## 1. Authentication & Session Management

Check: `SecurityConfig.java`, `DatabaseJwtAuthenticationConverter.java`, `UserDeactivationCheck.java`

| Check | What to Look For |
|-------|-----------------|
| SSO integration | Okta OIDC with PKCE, JWT validation via Spring Security resource server |
| Token validation | Access token validated for signature, expiry, issuer, audience |
| Provisioning gate | `checkProvisioningStatus()` enforces ACTIVE status; NOT_PROVISIONED and DEACTIVATED are fail-closed |
| User ID normalization | `UserIdNormalizer` lowercases at JWT extraction boundary (`Locale.ROOT`) |
| Role resolution | `UserRoleService` validates X-Active-Role against assigned roles; RoleResolution result type |
| Session boundaries | `PermissionService.reset()` called on login, logout, session-ended |
| Token auto-renewal | Frontend Okta SDK auto-renews tokens before expiry |

**Common vulnerabilities:**
- Missing provisioning gate (valid JWT but no local user record)
- Role header not validated for format (`^[A-Z_]+$`)
- Permissions not cleared on role switch or logout
- Dev-only override headers (`X-Override-Role`) active in production

---

## 2. Authorization & Access Control

Check: `@PreAuthorize` annotations, `PermissionResolver.java`, `role_permissions` table

| Check | What to Look For |
|-------|-----------------|
| Method security | Every `@RestController` method has `@PreAuthorize("hasPermissionForActiveRole(...)")` |
| Role-scoped permissions | Permissions resolved from `role_permissions` lookup for active role |
| Agency sovereignty | Purchasing agency controls its own approval chain; cross-agency access blocked |
| Row-level filtering | Queries scoped by agency/role (agency users see own agency data only) |
| Ownership checks | Edit/delete operations verify ownership or appropriate permission |
| IDOR prevention | UUIDs used for all public-facing identifiers (not sequential IDs) |

**Test pattern:** For each endpoint, verify:
1. Unauthenticated request returns 401
2. Wrong-role request returns 403
3. Other agency's resource returns 403/404

---

## 3. Input Validation & Injection

Check: `@Valid` annotations, DTO records with Bean Validation, `@Query` methods

| Check | What to Look For |
|-------|-----------------|
| Bean Validation | All `@RequestBody` parameters annotated with `@Valid` |
| Field constraints | `@NotNull`, `@NotBlank`, `@Size`, `@Pattern` on DTO fields |
| SQL injection | All queries use JPA/JPQL (parameterized); no string concatenation in queries |
| Path traversal | File paths constructed from UUIDs, not user input |
| JPQL injection | No dynamic JPQL construction with string concatenation |

**Red flags to search for:**
```
nativeQuery.*+              # String concatenation in native queries
"SELECT.*" + variable       # Dynamic query construction
.createNativeQuery(         # Native queries (verify parameterized)
eval(                       # Dynamic code execution (frontend)
bypassSecurityTrust         # Angular sanitizer bypass
```

---

## 4. API Security

Check: `SecurityConfig.java`, `CorsConfigurationSource`, response headers

| Check | What to Look For |
|-------|-----------------|
| CORS origins | Explicit allowlist in `CorsConfigurationSource`, not `"*"` |
| Security headers | Spring Security `headers()` DSL configures X-Content-Type-Options, X-Frame-Options, HSTS |
| Rate limiting | Auth and SCIM endpoints protected from brute force |
| API docs | Springdoc/Swagger UI disabled in production profile |
| Error responses | `GlobalExceptionHandler` returns RFC 7807 Problem Detail (no stack traces, no SQL, no paths) |
| CSRF | Stateless JWT architecture with CSRF disabled in Spring Security (verify stateless session) |

---

## 5. Data Protection & Secrets

Check: `application.yml`, `application-*.yml`, `.env`, `.gitignore`, `docker-compose.yml`

| Check | What to Look For |
|-------|-----------------|
| Secrets in config | All secrets via environment variables or Spring profiles, not in committed YAML |
| No hardcoded secrets | No API keys, passwords, or tokens in source code |
| .env in .gitignore | Environment files never committed |
| Logging safety | Secrets never logged (no `log.info("key={}", secret)`) |
| Error messages | Internal details never in API error responses |
| Database URL | Connection string with credentials never logged or returned |
| Okta config | Client ID in code is acceptable; client secret (if used) must be in env vars |

---

## 6. Frontend Security

Check: Angular components, interceptors, services, route guards

| Check | What to Look For |
|-------|-----------------|
| XSS prevention | No `bypassSecurityTrustHtml()` or similar without documented justification |
| No eval | No `eval()`, `Function()`, `document.write()`, or direct `innerHTML` with user input |
| Token handling | Okta SDK manages tokens; no tokens in localStorage or sessionStorage |
| Route guards | `OktaAuthGuard`, `permissionGuard()`, `roleGuard()` on all protected routes |
| Open redirects | No `window.location.href = userInput`; use Angular Router with validated paths |
| Error display | Generic messages to users, not raw API error details |
| Sensitive state | No passwords, tokens, or PII in signals, BehaviorSubjects, or component state |

**Search patterns:**
```
bypassSecurityTrust    # Angular sanitizer bypass
localStorage           # Token/secret storage check
sessionStorage         # Token/secret storage check
eval(                  # Code injection
innerHTML              # DOM manipulation (verify sanitized)
window.location        # Open redirect risk
```

---

## 7. File Upload Security

Check: Attachment controller and service classes in `attachment/` package

| Check | What to Look For |
|-------|-----------------|
| Size limit | Enforced via Spring `spring.servlet.multipart.max-file-size` |
| Content type | Validated against allowlist (not just extension) |
| Extension | Validated against allowlist, case-insensitive (`toLowerCase(Locale.ROOT)`) |
| Storage path | UUID-based filenames (no user-controlled paths) |
| Directory traversal | No user input in directory construction |
| Access control | Downloads require authentication and appropriate permission |

---

## 8. Infrastructure & Docker

Check: `Dockerfile`, `docker-compose.yml`, Kubernetes manifests (if any)

| Check | What to Look For |
|-------|-----------------|
| Non-root user | `USER` directive in production Dockerfiles |
| Minimal base | Alpine or slim variants (`node:22-alpine`, `eclipse-temurin:25-jre-alpine`) |
| No secrets in layers | No `COPY .env`, no `ENV SECRET=`, no `ARG PASSWORD=` |
| Multi-stage build | Build tools excluded from final image |
| Resource limits | `deploy.resources.limits` in Compose |
| DB port exposure | PostgreSQL port not exposed to host in production |
| Health checks | All services have health checks |
| Security options | `no-new-privileges:true`, `read_only` where possible |

---

## 9. Dependencies

```bash
# Backend (Java/Gradle)
./gradlew dependencyCheckAnalyze    # OWASP dependency check for CVEs
./gradlew dependencyUpdates         # Check for available updates

# Frontend (Node/npm)
npm audit                           # Check for known CVEs
npm outdated                        # Check for updates
```

Flag any package with known CVEs. Prioritize: authentication libraries, cryptography, web framework, Okta SDK.

---

## 10. Logging & Monitoring

| Check | What to Look For |
|-------|-----------------|
| Auth events | Failed logins logged with user ID (not password or token) |
| Permission denials | 403s logged with user ID, active role, and requested resource |
| Data access | Sensitive operations logged (admin actions, exports, approval decisions) |
| No secrets in logs | Passwords, tokens, API keys never in log output |
| Structured logging | SLF4J with structured format: `log.info("DOMAIN_ACTION: field={}", value)` |
| Trace context | Every error includes `traceId` for distributed tracing correlation |

---

## Report Template

After completing the audit, produce a report:

```markdown
# Security Audit Report — [Date]

## Summary
- Critical: [count]
- High: [count]
- Medium: [count]
- Low: [count]

## Findings

### [CRITICAL/HIGH/MEDIUM/LOW] — Finding Title
- **Location:** file:line
- **Description:** What the vulnerability is
- **Impact:** What an attacker could do
- **Recommendation:** How to fix it
- **Reference:** OWASP/CWE link if applicable
```
