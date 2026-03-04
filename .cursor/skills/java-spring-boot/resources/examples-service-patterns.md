# Examples: Service Patterns

Business logic layer patterns for Spring services.

---

## Basic Service Structure

```java
/**
 * Service for managing project lifecycle operations.
 */
@Service
public class ProjectService {
    private final ProjectRepository projectRepository;
    private final UserLookup userLookup;

    // Constructor injection (MANDATED)
    public ProjectService(ProjectRepository projectRepository, UserLookup userLookup) {
        this.projectRepository = projectRepository;
        this.userLookup = userLookup;
    }

    /**
     * Retrieves all active projects for the authenticated user's agency.
     *
     * @param userId the authenticated user's ID
     * @return list of active projects
     */
    public List<ProjectDTO> getActiveProjects(String userId) {
        UserInfo user = userLookup.getUser(userId);
        if (user == null) {
            throw new ResourceNotFoundException("User", userId);
        }
        List<Project> projects = projectRepository.findByAgencyIdAndIsActiveTrue(user.getAgencyId());
        return projects.stream()
            .map(this::mapToDTO)
            .toList();
    }

    private ProjectDTO mapToDTO(Project project) {
        return new ProjectDTO(
            project.getId(),
            project.getName(),
            project.getStatus()
        );
    }
}
```

---

## Method Naming Patterns

Follow consistent verb-noun patterns:

```java
@Service
public class WorkflowService {
    // Getters - retrieve data
    public Workflow getWorkflow(Long id) { ... }
    public List<Workflow> getAllWorkflows() { ... }
    public List<Workflow> findWorkflowsByStatus(WorkflowStatus status) { ... }
    
    // Mutations - modify data
    public Workflow saveWorkflow(WorkflowDTO dto) { ... }
    public Workflow updateWorkflow(Long id, WorkflowDTO dto) { ... }
    public void deleteWorkflow(Long id) { ... }
    
    // Actions - business operations
    public Workflow submitForApproval(Long workflowId) { ... }
    public Workflow approveWorkflow(Long workflowId, String approverId) { ... }
    public Workflow rejectWorkflow(Long workflowId, String reason) { ... }
    
    // Transformations
    public WorkflowDTO mapWorkflowToDTO(Workflow workflow) { ... }
}
```

---

## Transaction Management

```java
@Service
public class ProcurementService {
    private final WorkflowRepository workflowRepository;
    private final AuditLogRepository auditLogRepository;

    public ProcurementService(WorkflowRepository workflowRepository, 
                              AuditLogRepository auditLogRepository) {
        this.workflowRepository = workflowRepository;
        this.auditLogRepository = auditLogRepository;
    }

    /**
     * Submits a workflow for approval and creates an audit record.
     * Both operations occur in a single transaction.
     *
     * @param workflowId the workflow to submit
     * @param submitterId the user submitting
     * @return the updated workflow
     */
    @Transactional
    public Workflow submitForApproval(Long workflowId, String submitterId) {
        // System Invariant: the workflowId came from a verified internal source, must exist
        Workflow workflow = workflowRepository.findById(workflowId)
            .orElseThrow(() -> new ResourceNotFoundException("Workflow", workflowId));
        
        // ... success path
        return saved;
    }

    /**
     * Business lookup: the ID is from user input, may not exist.
     */
    @Transactional(readOnly = true)
    public Optional<Workflow> findWorkflow(Long workflowId) {
        return workflowRepository.findById(workflowId);
    }

    /**
     * Read-only transaction for queries.
     */
    @Transactional(readOnly = true)
    public List<WorkflowSummary> getWorkflowSummaries(String agencyId) {
        return workflowRepository.findSummariesByAgencyId(agencyId);
    }
}
```

---

## Validation in Services

Validate business rules at the service layer:

```java
// Business outcome as data (Tiger-style)
public record ApprovalResult(ApprovalStatus status, String reason, @Nullable Workflow workflow) {}

@Service
public class ApprovalService {
    private static final int MAX_APPROVAL_AMOUNT = 100_000;

    /**
     * Approves a workflow if business rules are satisfied.
     *
     * @param workflowId the workflow to approve
     * @param approverId the approving user
     * @return result record containing status and data
     */
    public ApprovalResult approveWorkflow(Long workflowId, String approverId) {
        // Guard clauses (valid throws for boundary violations)
        if (workflowId == null) throw new IllegalArgumentException("workflowId required");

        Workflow workflow = workflowRepository.findById(workflowId).orElse(null);
        if (workflow == null) {
            return new ApprovalResult(ApprovalStatus.NOT_FOUND, "Workflow not found", null);
        }
        
        // Business rule outcomes as data
        if (workflow.getStatus() != WorkflowStatus.PENDING_APPROVAL) {
            return new ApprovalResult(ApprovalStatus.INVALID_STATE, "Workflow is not pending approval", null);
        }
        
        // import java.util.Objects;
        if (Objects.equals(workflow.getSubmittedBy(), approverId)) {
            return new ApprovalResult(ApprovalStatus.DENIED, "Cannot approve your own submission", null);
        }
        
        if (workflow.getAmount() > MAX_APPROVAL_AMOUNT) {
            return new ApprovalResult(ApprovalStatus.EXCEEDS_LIMIT, "Amount exceeds single-approver limit", null);
        }
        
        workflow.setStatus(WorkflowStatus.APPROVED);
        workflow.setApprovedBy(approverId);
        workflow.setApprovedDate(LocalDateTime.now());
        
        return new ApprovalResult(ApprovalStatus.APPROVED, null, workflowRepository.save(workflow));
    }
}
```

---

## DTO Mapping with Records

Use Java records for immutable DTOs:

```java
/**
 * Data transfer object for project responses.
 *
 * @param id the project identifier
 * @param name the project display name
 * @param status current project status
 * @param agencyName the owning agency name
 */
public record ProjectDTO(
    Long id,
    String name,
    ProjectStatus status,
    String agencyName
) {}

@Service
public class ProjectService {
    /**
     * Maps entity to DTO.
     */
    private ProjectDTO mapToDTO(Project project) {
        Agency agency = project.getAgency();
        return new ProjectDTO(
            project.getId(),
            project.getName(),
            project.getStatus(),
            agency != null ? agency.getName() : null
        );
    }
    
    /**
     * Maps DTO to entity for creation.
     */
    private Project mapToEntity(CreateProjectDTO dto, Agency agency) {
        return Project.builder()
            .name(dto.name())
            .description(dto.description())
            .agency(agency)
            .status(ProjectStatus.DRAFT)
            .isActive(true)
            .createdDate(LocalDateTime.now())
            .build();
    }
}
```

---

## External Service Integration

```java
/**
 * Service for enriching data with external user information.
 */
@Service
public class UserEnrichmentService {
    private final UserLookup userLookup;

    public UserEnrichmentService(UserLookup userLookup) {
        this.userLookup = userLookup;
    }

    /**
     * Enriches workflow with submitter details from external service.
     *
     * @param workflow the workflow to enrich
     * @return enriched DTO
     */
    public WorkflowWithUserDTO enrichWithUserInfo(Workflow workflow) {
        UserInfo submitter = userLookup.getUser(workflow.getSubmittedBy());
        UserInfo approver = workflow.getApprovedBy() != null 
            ? userLookup.getUser(workflow.getApprovedBy()) 
            : null;
        
        return new WorkflowWithUserDTO(
            workflow.getId(),
            workflow.getStatus(),
            submitter != null ? submitter.getDisplayName() : null,
            approver != null ? approver.getDisplayName() : null
        );
    }
}
```

---

## Anti-Patterns

- Returning entities directly (always map to DTOs)
- Business logic in controllers or repositories
- Catching and swallowing exceptions silently
- Using field injection instead of constructor injection
- Mixing transaction boundaries inappropriately
- Service methods doing too many things (violating SRP)
