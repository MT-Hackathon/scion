# Reference: Lombok Patterns

Lombok annotations for reducing boilerplate in Spring Boot applications.

---

## Entity with @Builder

```java
@Entity
@Table(name = "project")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Project {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    @Column(nullable = false)
    private String name;
    
    private String description;
    
    @Enumerated(EnumType.STRING)
    private ProjectStatus status;
    
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "agency_id")
    private Agency agency;
    
    @Column(name = "is_active")
    private Boolean isActive;
    
    @Column(name = "created_date")
    private LocalDateTime createdDate;
}

// Usage
Project project = Project.builder()
    .name("New Project")
    .description("Description here")
    .status(ProjectStatus.DRAFT)
    .agency(agency)
    .isActive(true)
    .createdDate(LocalDateTime.now())
    .build();
```

---

## @Data for Simple Classes

`@Data` combines `@Getter`, `@Setter`, `@ToString`, `@EqualsAndHashCode`, and `@RequiredArgsConstructor`:

```java
@Data
public class UserInfo {
    private final String userId;      // Required (final)
    private final String displayName; // Required (final)
    private String email;             // Optional
    private String phone;             // Optional
}

// Creates constructor for final fields
UserInfo user = new UserInfo("user123", "John Doe");
user.setEmail("john@example.com");
```

---

## Java Records vs Lombok

Prefer **Java records** for DTOs (immutable, concise):

```java
// Java Record (preferred for DTOs)
public record ProjectDTO(
    Long id,
    String name,
    ProjectStatus status,
    String agencyName
) {}

// Equivalent Lombok (use when you need mutability or inheritance)
@Data
@AllArgsConstructor
public class ProjectDTO {
    private Long id;
    private String name;
    private ProjectStatus status;
    private String agencyName;
}
```

**When to use records:**
- DTOs (request/response bodies)
- Value objects
- Immutable data carriers

**When to use Lombok:**
- JPA entities (need no-arg constructor, setters)
- Classes requiring inheritance
- Classes needing builder pattern with complex defaults

---

## @Builder with Defaults

```java
@Entity
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Workflow {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    private String title;
    
    @Builder.Default
    @Enumerated(EnumType.STRING)
    private WorkflowStatus status = WorkflowStatus.DRAFT;
    
    @Builder.Default
    private Boolean isActive = true;
    
    @Builder.Default
    private LocalDateTime createdDate = LocalDateTime.now();
}

// Defaults are applied
Workflow workflow = Workflow.builder()
    .title("New Workflow")
    .build();
// status = DRAFT, isActive = true, createdDate = now
```

---

## @Slf4j for Logging

```java
@Service
@Slf4j
public class WorkflowService {
    
    public Workflow submitForApproval(Long workflowId, String submitterId) {
        log.info("Submitting workflow {} for approval by {}", workflowId, submitterId);
        
        try {
            // ... logic
            log.debug("Workflow {} status updated to PENDING", workflowId);
            return workflow;
        } catch (Exception e) {
            log.error("Failed to submit workflow {}: {}", workflowId, e.getMessage(), e);
            throw e;
        }
    }
}
```

---

## @RequiredArgsConstructor for DI

```java
@Service
@RequiredArgsConstructor
public class ProjectService {
    private final ProjectRepository projectRepository;  // Injected
    private final UserLookup userLookup;                // Injected
    private final AuditLogRepository auditLogRepository; // Injected
    
    // Constructor generated automatically:
    // public ProjectService(ProjectRepository projectRepository, 
    //                       UserLookup userLookup, 
    //                       AuditLogRepository auditLogRepository) { ... }
}
```

---

## @ToString Exclusions

Avoid logging sensitive data or circular references:

```java
@Entity
@Getter
@Setter
@ToString(exclude = {"password", "agency"})
public class User {
    private Long id;
    private String username;
    private String password;     // Excluded from toString
    
    @ManyToOne
    private Agency agency;       // Excluded to prevent circular reference
}
```

---

## @EqualsAndHashCode for Entities

For JPA entities, use only the ID for equality:

```java
@Entity
@Getter
@Setter
@EqualsAndHashCode(onlyExplicitlyIncluded = true)
public class Project {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @EqualsAndHashCode.Include
    private Long id;
    
    private String name;
    // Other fields excluded from equals/hashCode
}
```

---

## Lombok Configuration

Create `lombok.config` in project root:

```properties
# Generate @Generated annotations for code coverage
lombok.addLombokGeneratedAnnotation = true

# Use field access for getters/setters
lombok.accessors.fluent = false

# Generate copy methods for @With
lombok.anyConstructor.addConstructorProperties = true
```

---

## Common Annotations Summary

| Annotation | Purpose | Use Case |
|------------|---------|----------|
| `@Getter` / `@Setter` | Generate accessors | Entities, mutable classes |
| `@Data` | All-in-one for POJOs | Simple data classes |
| `@Builder` | Builder pattern | Complex object construction |
| `@NoArgsConstructor` | No-arg constructor | JPA entities |
| `@AllArgsConstructor` | All-args constructor | Immutable classes |
| `@RequiredArgsConstructor` | Final-field constructor | Spring services (DI) |
| `@Slf4j` | Logger field | Any class needing logging |
| `@ToString` | toString() method | Debugging |
| `@EqualsAndHashCode` | equals/hashCode | Value objects, entities |

---

## Anti-Patterns

- Using `@Data` on JPA entities (generates problematic `equals`/`hashCode`)
- Missing `@NoArgsConstructor` on JPA entities
- Using Lombok for DTOs when Java records would suffice
- Not excluding sensitive fields from `@ToString`
- Circular references in `@ToString` causing stack overflow
