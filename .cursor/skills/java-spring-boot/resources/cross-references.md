# Cross-References

Related skills and rules for Java Spring Boot development.

---

## Related Skills

### Security

**Skill**: [security](../../security/SKILL.md)

Covers credential security, API authentication patterns, and .env management. For Java/Spring:

- JWT token verification in Spring Security filters
- Okta integration for OAuth2/OIDC
- Role-based access control with `@PreAuthorize`
- Secure credential storage via environment variables

### Testing & Debugging

**Skill**: [testing-debugging](../../testing-debugging/SKILL.md)

Universal testing philosophy that applies to Java:

- Diagnostic order when tests fail (environment → config → code)
- Anti-cheating mandate (don't read tests before writing code)
- Fix code, not tests

### Container

**Skill**: [container](../../container/SKILL.md)

Docker/Podman patterns for Spring Boot:

- Multi-stage Dockerfile for Spring Boot JARs
- PostgreSQL container for local development
- Health check configuration with Spring Actuator

### CI/CD Pipeline

**Skill**: [ci-pipeline](../../ci-pipeline/SKILL.md)

GitLab CI patterns for Java projects:

- Gradle build stages
- Test execution and reporting
- Container image builds

---

## Related Rules

### Universal Constitution

**Rule**: [012-constitution-universal](../../../rules/012-constitution-universal/RULE.mdc)

Applies to all languages including Java:

- Code quality mandates
- Search-first development
- Documentation standards

### TypeScript Constitution

**Rule**: [130-constitution-typescript](../../../rules/130-constitution-typescript/RULE.mdc)

While Java-specific, shares these TypeScript patterns:

- Strict null checking philosophy (matches Java's Optional usage)
- Import organization principles
- Naming conventions (largely aligned)

---

## Java-Specific Integrations

### Spring Security with Okta

Complement the Angular frontend's Okta integration using the `SecurityConfig` blueprint:

→ **Blueprint**: [SecurityConfig](../blueprints/security-config.java) — OAuth2 resource server with JWT converter wiring and Lambda DSL filter chain.

### Shared DTOs with Frontend

When Angular frontend and Spring backend share data shapes:

```java
// Backend DTO
public record WorkflowDTO(
    Long id,
    String title,
    WorkflowStatus status,
    String submittedByName,
    LocalDateTime submittedDate
) {}

// Corresponds to Angular interface:
// interface WorkflowDTO {
//   id: number;
//   title: string;
//   status: WorkflowStatus;
//   submittedByName: string;
//   submittedDate: string; // ISO 8601
// }
```

### API Contract Alignment

Ensure backend responses match frontend expectations:

| Backend (Java) | Frontend (Angular) | Notes |
|---------------|-------------------|-------|
| `LocalDateTime` | `string` | Serialize as ISO 8601 |
| `Long` | `number` | Check for precision loss > 2^53 |
| `enum` | `string \| enum` | Use `@JsonValue` for custom serialization |
| `Optional.empty()` | `null` | Configure Jackson for null handling |

---

## Build & Environment

### Gradle Commands

```bash
# Development
./gradlew bootRun                    # Start with dev profile
./gradlew bootRun --args='--spring.profiles.active=local'

# Testing
./gradlew test                       # Run all tests
./gradlew test --tests "*ServiceTest" # Run specific tests
./gradlew test --info                # Verbose output

# Build
./gradlew build                      # Full build with tests
./gradlew build -x test              # Skip tests
./gradlew bootJar                    # Build executable JAR

# Dependencies
./gradlew dependencies               # Show dependency tree
./gradlew dependencyUpdates          # Check for updates (with plugin)
```

### Environment Configuration

```yaml
# application.yml - base configuration
spring:
  application:
    name: doa-procurement-workflow-api
  profiles:
    active: ${SPRING_PROFILES_ACTIVE:local}

---
# application-local.yml - local development
spring:
  config:
    activate:
      on-profile: local
  datasource:
    url: jdbc:postgresql://localhost:5432/procurement
    username: ${DB_USERNAME:postgres}
    password: ${DB_PASSWORD:postgres}

---
# application-test.yml - test environment
spring:
  config:
    activate:
      on-profile: test
  datasource:
    url: jdbc:h2:mem:testdb
    driver-class-name: org.h2.Driver
```

