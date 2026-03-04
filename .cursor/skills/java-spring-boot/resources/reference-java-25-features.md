# Reference: Java 25 Features

Modern Java features for Spring Boot 4.0 development.

---

## Java Records (Java 14+, finalized 16)

Immutable data carriers with automatic equals/hashCode/toString:

```java
/**
 * Response DTO for project data.
 *
 * @param id project identifier
 * @param name project display name
 * @param status current status
 */
public record ProjectDTO(
    Long id,
    String name,
    ProjectStatus status
) {}

// Compact constructor for validation
public record CreateProjectDTO(
    String name,
    String description,
    String agencyId
) {
    public CreateProjectDTO {
        Objects.requireNonNull(name, "Name is required");
        if (name.length() < 3) {
            throw new IllegalArgumentException("Name must be at least 3 characters");
        }
    }
}

// Record with additional methods
public record UserInfo(String userId, String displayName, String email) {
    public String getInitials() {
        return displayName.chars()
            .filter(Character::isUpperCase)
            .limit(2)
            .collect(StringBuilder::new, StringBuilder::appendCodePoint, StringBuilder::append)
            .toString();
    }
}
```

---

## Pattern Matching for instanceof (Java 16+)

```java
// Before
if (obj instanceof String) {
    String s = (String) obj;
    return s.length();
}

// After - pattern variable automatically in scope
if (obj instanceof String s) {
    return s.length();
}

// With negation
if (!(obj instanceof String s)) {
    throw new IllegalArgumentException("Expected String");
}
// s is in scope here

// In complex conditions
if (obj instanceof String s && s.length() > 5) {
    return s.toUpperCase();
}
```

---

## Pattern Matching for switch (Java 21+)

```java
// Type patterns in switch
public String describeWorkflow(Object obj) {
    return switch (obj) {
        case Workflow w -> "Workflow: " + w.getTitle();
        case Project p -> "Project: " + p.getName();
        case String s -> "String: " + s;
        case null -> "null value";
        default -> "Unknown: " + obj.getClass().getSimpleName();
    };
}

// Guard patterns
public String categorizeAmount(Number amount) {
    return switch (amount) {
        case Integer i when i < 0 -> "negative integer";
        case Integer i when i == 0 -> "zero";
        case Integer i -> "positive integer: " + i;
        case Double d when d < 0 -> "negative double";
        case Double d -> "non-negative double: " + d;
        default -> "other number type";
    };
}

// Record patterns (destructuring)
public String formatProject(Object obj) {
    return switch (obj) {
        case ProjectDTO(Long id, String name, ProjectStatus status) 
            -> String.format("Project #%d: %s (%s)", id, name, status);
        default -> "Not a project";
    };
}
```

---

## Sealed Classes (Java 17+)

Restrict which classes can extend/implement:

```java
/**
 * Base class for workflow actions.
 */
public sealed abstract class WorkflowAction 
    permits SubmitAction, ApproveAction, RejectAction {
    
    protected final String performedBy;
    protected final LocalDateTime performedAt;
    
    protected WorkflowAction(String performedBy) {
        this.performedBy = performedBy;
        this.performedAt = LocalDateTime.now();
    }
}

public final class SubmitAction extends WorkflowAction {
    public SubmitAction(String submittedBy) {
        super(submittedBy);
    }
}

public final class ApproveAction extends WorkflowAction {
    private final String comments;
    
    public ApproveAction(String approvedBy, String comments) {
        super(approvedBy);
        this.comments = comments;
    }
}

public final class RejectAction extends WorkflowAction {
    private final String reason;
    
    public RejectAction(String rejectedBy, String reason) {
        super(rejectedBy);
        this.reason = reason;
    }
}

// Exhaustive switch (compiler knows all subtypes)
public String describeAction(WorkflowAction action) {
    return switch (action) {
        case SubmitAction s -> "Submitted by " + s.performedBy;
        case ApproveAction a -> "Approved by " + a.performedBy + ": " + a.comments;
        case RejectAction r -> "Rejected by " + r.performedBy + ": " + r.reason;
        // No default needed - all cases covered
    };
}
```

---

## Virtual Threads (Java 21+)

Lightweight threads for high-concurrency scenarios:

```java
// Spring Boot 4.0 can use virtual threads by default
// application.yml:
// spring:
//   threads:
//     virtual:
//       enabled: true

// Manual virtual thread creation
@Service
public class BatchProcessingService {
    
    /**
     * Process items concurrently using virtual threads.
     */
    public void processItemsConcurrently(List<Item> items) {
        try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
            List<Future<ProcessResult>> futures = items.stream()
                .map(item -> executor.submit(() -> processItem(item)))
                .toList();
            
            for (Future<ProcessResult> future : futures) {
                try {
                    ProcessResult result = future.get();
                    log.info("Processed: {}", result);
                } catch (ExecutionException e) {
                    log.error("Processing failed", e.getCause());
                }
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new RuntimeException("Processing interrupted", e);
        }
    }
    
    private ProcessResult processItem(Item item) {
        // I/O-bound work benefits most from virtual threads
        return externalService.process(item);
    }
}
```

---

## Text Blocks (Java 15+)

Multi-line strings for SQL, JSON, etc.:

```java
// SQL queries
@Query(value = """
    SELECT w.id, w.title, w.status, u.display_name as submitter_name
    FROM workflow w
    LEFT JOIN app_user u ON u.user_id = w.submitted_by
    WHERE w.agency_id = :agencyId
      AND w.status = 'PENDING'
    ORDER BY w.submitted_date DESC
    """, nativeQuery = true)
List<WorkflowSummaryProjection> findPendingByAgency(@Param("agencyId") String agencyId);

// JSON in tests
String expectedJson = """
    {
        "id": 1,
        "name": "Test Project",
        "status": "ACTIVE"
    }
    """;

// Error messages
throw new BusinessRuleException("""
    Cannot approve workflow:
    - Workflow ID: %d
    - Current status: %s
    - Required status: PENDING_APPROVAL
    """.formatted(workflowId, workflow.getStatus()));
```

---

## Helpful NullPointerExceptions (Java 14+)

JVM automatically provides detailed NPE messages:

```java
// If workflow.getSubmittedBy().getDisplayName() throws NPE:
// Before: NullPointerException
// After:  Cannot invoke "String getDisplayName()" because the return value of 
//         "Workflow.getSubmittedBy()" is null
```

Enable in `JAVA_OPTS` if not default:
```
-XX:+ShowCodeDetailsInExceptionMessages
```

---

## String Methods

```java
// Indentation (Java 12+)
String indented = text.indent(4);     // Add 4 spaces to each line
String stripped = text.stripIndent(); // Remove common leading whitespace

// Transform (Java 12+)
String result = input
    .transform(String::trim)
    .transform(s -> s.isEmpty() ? "default" : s)
    .transform(String::toUpperCase);

// Formatted (Java 15+) - instance method
String message = "Hello, %s! You have %d messages."
    .formatted(userName, messageCount);

// isBlank (Java 11+)
if (input.isBlank()) {
    throw new IllegalArgumentException("Input cannot be blank");
}
```

---

## Collection Factory Methods

```java
// Immutable collections (Java 9+)
List<String> statuses = List.of("DRAFT", "PENDING", "APPROVED");
Set<String> allowedRoles = Set.of("ADMIN", "APPROVER", "VIEWER");
Map<String, Integer> limits = Map.of(
    "small", 1000,
    "medium", 5000,
    "large", 10000
);

// For more than 10 entries
Map<String, Integer> largeLimits = Map.ofEntries(
    Map.entry("tier1", 100),
    Map.entry("tier2", 500),
    // ... more entries
    Map.entry("tier11", 50000)
);
```

---

## Stream Improvements

```java
// toList() (Java 16+) - shorter than Collectors.toList()
List<String> names = projects.stream()
    .map(Project::getName)
    .toList();

// mapMulti (Java 16+) - replace flatMap for simple cases
List<String> allTags = projects.stream()
    .<String>mapMulti((project, consumer) -> {
        project.getTags().forEach(consumer);
    })
    .distinct()
    .toList();

// takeWhile / dropWhile (Java 9+)
List<Workflow> recent = workflows.stream()
    .sorted(Comparator.comparing(Workflow::getCreatedDate).reversed())
    .takeWhile(w -> w.getCreatedDate().isAfter(cutoffDate))
    .toList();
```

---

## When to Use Modern Features

| Feature | Use When |
|---------|----------|
| Records | DTOs, value objects, immutable data |
| Pattern matching switch | Processing different types/states |
| Sealed classes | Restricted type hierarchies with exhaustive matching |
| Virtual threads | I/O-bound concurrent operations |
| Text blocks | Multi-line SQL, JSON, error messages |
| `var` | Local variables where type is obvious from RHS |

---

## Anti-Patterns

- Using `var` when type isn't obvious from context
- Overusing virtual threads for CPU-bound work
- Mutable records (defeats the purpose)
- Missing `permits` clause on sealed classes
- Text blocks with inconsistent indentation
