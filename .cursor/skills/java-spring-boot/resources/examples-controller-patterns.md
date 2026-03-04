# Examples: Controller Patterns

REST API controller patterns for Spring WebMVC.

---

## Basic Controller Structure

```java
import org.springframework.security.access.prepost.PreAuthorize;

/**
 * REST API for project management operations.
 */
@RestController
@RequestMapping("/api/v1/projects")
public class ProjectController {
    private final ProjectService projectService;

    public ProjectController(ProjectService projectService) {
        this.projectService = projectService;
    }

    /**
     * Retrieves all projects for the authenticated user.
     *
     * @return list of projects
     */
    @PreAuthorize("isAuthenticated()")
    @GetMapping
    public ResponseEntity<List<ProjectDTO>> getAllProjects() {
        List<ProjectDTO> projects = projectService.getAllProjects();
        return ResponseEntity.ok(projects);
    }

    /**
     * Retrieves a specific project by ID.
     *
     * @param id the project identifier
     * @return the project
     */
    @PreAuthorize("isAuthenticated()")
    @GetMapping("/{id}")
    public ResponseEntity<ProjectDTO> getProject(@PathVariable Long id) {
        ProjectDTO project = projectService.getProject(id);
        return ResponseEntity.ok(project);
    }

    /**
     * Creates a new project.
     *
     * @param dto the project data
     * @return the created project
     */
    @PreAuthorize("isAuthenticated()")
    @PostMapping
    public ResponseEntity<ProjectDTO> createProject(@Valid @RequestBody CreateProjectDTO dto) {
        ProjectDTO created = projectService.createProject(dto);
        URI location = URI.create("/api/v1/projects/" + created.id());
        return ResponseEntity.created(location).body(created);
    }

    /**
     * Updates an existing project.
     *
     * @param id the project identifier
     * @param dto the updated data
     * @return the updated project
     */
    @PreAuthorize("isAuthenticated()")
    @PutMapping("/{id}")
    public ResponseEntity<ProjectDTO> updateProject(
            @PathVariable Long id, 
            @Valid @RequestBody UpdateProjectDTO dto) {
        ProjectDTO updated = projectService.updateProject(id, dto);
        return ResponseEntity.ok(updated);
    }

    /**
     * Deletes a project.
     *
     * @param id the project identifier
     * @return no content
     */
    @PreAuthorize("hasRole('ADMIN')")
    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteProject(@PathVariable Long id) {
        projectService.deleteProject(id);
        return ResponseEntity.noContent().build();
    }
}
```

---

## Request DTOs with Validation

```java
/**
 * Request body for creating a project.
 *
 * @param name project name (required, 3-100 chars)
 * @param description optional description
 * @param agencyId owning agency (required)
 */
public record CreateProjectDTO(
    @NotBlank(message = "Name is required")
    @Size(min = 3, max = 100, message = "Name must be 3-100 characters")
    String name,
    
    @Size(max = 500, message = "Description cannot exceed 500 characters")
    String description,
    
    @NotBlank(message = "Agency ID is required")
    String agencyId
) {}
```

---

## Pagination Endpoints

```java
import org.springframework.security.access.prepost.PreAuthorize;

@RestController
@RequestMapping("/api/v1/audit-logs")
public class AuditLogController {
    private final AuditLogService auditLogService;

    public AuditLogController(AuditLogService auditLogService) {
        this.auditLogService = auditLogService;
    }

    /**
     * Retrieves paginated audit logs.
     *
     * @param page page number (0-indexed)
     * @param size page size
     * @param sort sort field and direction
     * @return page of audit logs
     */
    @PreAuthorize("isAuthenticated()")
    @GetMapping
    public ResponseEntity<Page<AuditLogDTO>> getAuditLogs(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size,
            @RequestParam(defaultValue = "createdDate,desc") String sort) {
        
        Pageable pageable = createPageable(page, size, sort);
        Page<AuditLogDTO> logs = auditLogService.getAuditLogs(pageable);
        return ResponseEntity.ok(logs);
    }

    private Pageable createPageable(int page, int size, String sort) {
        String[] parts = sort.split(",");
        Sort.Direction direction = parts.length > 1 && parts[1].equalsIgnoreCase("asc") 
            ? Sort.Direction.ASC 
            : Sort.Direction.DESC;
        return PageRequest.of(page, Math.min(size, 100), Sort.by(direction, parts[0]));
    }
}
```

---

## Action Endpoints

For operations beyond CRUD:

```java
import org.springframework.security.access.prepost.PreAuthorize;

@RestController
@RequestMapping("/api/v1/workflows")
public class WorkflowController {
    private final WorkflowService workflowService;

    public WorkflowController(WorkflowService workflowService) {
        this.workflowService = workflowService;
    }

    /**
     * Submits a workflow for approval.
     *
     * @param id the workflow identifier
     * @return the updated workflow
     */
    @PreAuthorize("isAuthenticated()")
    @PostMapping("/{id}/submit")
    public ResponseEntity<WorkflowDTO> submitForApproval(@PathVariable Long id) {
        WorkflowDTO workflow = workflowService.submitForApproval(id);
        return ResponseEntity.ok(workflow);
    }

    /**
     * Approves a workflow.
     *
     * @param id the workflow identifier
     * @return the approved workflow
     */
    @PreAuthorize("hasAnyRole('ADMIN','APPROVER')")
    @PostMapping("/{id}/approve")
    public ResponseEntity<?> approve(@PathVariable Long id) {
        ApprovalResult result = workflowService.approve(id);
        return switch (result.status()) {
            case APPROVED -> ResponseEntity.ok(result.workflow());
            case NOT_FOUND -> ResponseEntity.notFound().build();
            case INVALID_STATE -> ResponseEntity.status(HttpStatus.CONFLICT)
                    .body(new ErrorResponse("INVALID_STATE", result.reason(), LocalDateTime.now()));
            case DENIED, EXCEEDS_LIMIT -> ResponseEntity.status(HttpStatus.FORBIDDEN)
                    .body(new ErrorResponse("PERMISSION_DENIED", result.reason(), LocalDateTime.now()));
        };
    }

    /**
     * Rejects a workflow with a reason.
     *
     * @param id the workflow identifier
     * @param dto rejection details
     * @return the rejected workflow
     */
    @PreAuthorize("hasAnyRole('ADMIN','APPROVER')")
    @PostMapping("/{id}/reject")
    public ResponseEntity<WorkflowDTO> reject(
            @PathVariable Long id,
            @Valid @RequestBody RejectWorkflowDTO dto) {
        WorkflowDTO workflow = workflowService.reject(id, dto.reason());
        return ResponseEntity.ok(workflow);
    }
}
```

---

## Global Exception Handling

```java
/**
 * Global exception handler for REST API errors.
 */
@RestControllerAdvice
public class GlobalExceptionHandler {

    /**
     * Handles resource not found exceptions (guard clause / system invariant violations).
     * For expected "not found" business outcomes, use result types instead.
     */
    @ExceptionHandler(ResourceNotFoundException.class)
    public ResponseEntity<ErrorResponse> handleNotFound(ResourceNotFoundException ex) {
        ErrorResponse error = new ErrorResponse(
            "NOT_FOUND",
            ex.getMessage(),
            LocalDateTime.now()
        );
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(error);
    }

    /**
     * Handles validation errors (boundary violations).
     */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ErrorResponse> handleValidation(MethodArgumentNotValidException ex) {
        String message = ex.getBindingResult().getFieldErrors().stream()
            .map(error -> error.getField() + ": " + error.getDefaultMessage())
            .collect(Collectors.joining(", "));
        
        ErrorResponse error = new ErrorResponse(
            "VALIDATION_ERROR",
            message,
            LocalDateTime.now()
        );
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(error);
    }
}

/**
 * Standard error response structure.
 */
public record ErrorResponse(
    String code,
    String message,
    LocalDateTime timestamp
) {}
```

---

## Response Status Codes

| Operation | Success | Common Errors |
|-----------|---------|---------------|
| GET (single) | 200 OK | 404 Not Found |
| GET (list) | 200 OK | - |
| POST (create) | 201 Created | 400 Bad Request, 422 Unprocessable |
| PUT (update) | 200 OK | 400, 404, 422 |
| DELETE | 204 No Content | 404 Not Found |
| POST (action) | 200 OK | 400, 404, 422 |

---

## Anti-Patterns

- Business logic in controllers (delegate to services)
- Returning entities instead of DTOs
- Missing `@Valid` on request body parameters
- Inconsistent response structures
- Missing error handling
- Hard-coding status codes instead of using `HttpStatus` enum
