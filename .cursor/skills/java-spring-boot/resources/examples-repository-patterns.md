# Examples: Repository Patterns

Spring Data JPA repository patterns for data access.

---

## Basic Repository Interface

```java
/**
 * Contract for working with the agency data store.
 */
@Repository
public interface AgencyRepository extends JpaRepository<Agency, String> {
    /**
     * Find all agencies by the active flag.
     *
     * @param isActive if the agency is currently in use or not
     * @return all applicable agencies
     */
    List<Agency> findAllByIsActive(Boolean isActive);
}
```

---

## Query Method Naming

Spring Data JPA auto-generates queries from method names:

```java
@Repository
public interface ProjectRepository extends JpaRepository<Project, Long> {
    // Simple property match
    List<Project> findByStatus(ProjectStatus status);
    
    // Multiple conditions
    List<Project> findByStatusAndAgencyId(ProjectStatus status, String agencyId);
    
    // Boolean flags
    List<Project> findAllByIsActiveTrue();
    
    // Ordering
    List<Project> findByAgencyIdOrderByCreatedDateDesc(String agencyId);
    
    // Optional result
    Optional<Project> findByProjectCode(String code);
    
    // Existence check
    boolean existsByProjectCode(String code);
    
    // Count
    long countByStatus(ProjectStatus status);
}
```

---

## Custom JPQL Queries

For complex queries that can't be expressed via method naming:

```java
@Repository
public interface WorkflowRepository extends JpaRepository<Workflow, Long> {
    /**
     * Find workflows pending approval for longer than the threshold.
     *
     * @param threshold the date threshold
     * @return overdue workflows
     */
    @Query("SELECT w FROM Workflow w WHERE w.status = 'PENDING' AND w.submittedDate < :threshold")
    List<Workflow> findOverduePendingWorkflows(@Param("threshold") LocalDateTime threshold);
    
    /**
     * Find workflows with their associated approvals eagerly loaded.
     *
     * @param workflowId the workflow identifier
     * @return workflow with approvals
     */
    @Query("SELECT w FROM Workflow w LEFT JOIN FETCH w.approvals WHERE w.id = :id")
    Optional<Workflow> findByIdWithApprovals(@Param("id") Long workflowId);
}
```

---

## Native Queries

When JPQL isn't sufficient (use sparingly):

```java
@Repository
public interface ReportRepository extends JpaRepository<Report, Long> {
    /**
     * Get agency summary statistics using native SQL.
     *
     * @param agencyId the agency identifier
     * @return summary projection
     */
    @Query(value = """
        SELECT a.agency_id, a.name, COUNT(p.id) as project_count
        FROM agency a
        LEFT JOIN project p ON p.agency_id = a.agency_id
        WHERE a.agency_id = :agencyId
        GROUP BY a.agency_id, a.name
        """, nativeQuery = true)
    AgencySummaryProjection getAgencySummary(@Param("agencyId") String agencyId);
}
```

---

## Projections

Use projections to return only needed fields:

```java
/**
 * Projection for project list views (avoids loading full entity).
 */
public interface ProjectSummaryProjection {
    Long getId();
    String getProjectCode();
    String getName();
    ProjectStatus getStatus();
}

@Repository
public interface ProjectRepository extends JpaRepository<Project, Long> {
    /**
     * Get lightweight project summaries for an agency.
     *
     * @param agencyId the agency identifier
     * @return project summaries
     */
    List<ProjectSummaryProjection> findSummariesByAgencyId(String agencyId);
}
```

---

## Pagination and Sorting

```java
@Repository
public interface AuditLogRepository extends JpaRepository<AuditLog, Long> {
    /**
     * Find audit logs with pagination.
     *
     * @param agencyId the agency to filter by
     * @param pageable pagination parameters
     * @return page of audit logs
     */
    Page<AuditLog> findByAgencyId(String agencyId, Pageable pageable);
}

// Usage in service:
Pageable pageable = PageRequest.of(0, 20, Sort.by("createdDate").descending());
Page<AuditLog> logs = auditLogRepository.findByAgencyId(agencyId, pageable);
```

---

## Modifying Queries

For bulk updates/deletes:

```java
@Repository
public interface NotificationRepository extends JpaRepository<Notification, Long> {
    /**
     * Mark all notifications as read for a user.
     *
     * @param userId the user identifier
     * @return count of updated records
     */
    // Note: userId parameter must be normalized to lowercase (see DatabaseJwtAuthenticationConverter)
    @Modifying
    @Query("UPDATE Notification n SET n.isRead = true WHERE n.userId = :userId AND n.isRead = false")
    int markAllAsRead(@Param("userId") String userId);
    
    /**
     * Delete old notifications.
     *
     * @param cutoffDate notifications older than this are deleted
     */
    @Modifying
    @Query("DELETE FROM Notification n WHERE n.createdDate < :cutoffDate")
    void deleteOlderThan(@Param("cutoffDate") LocalDateTime cutoffDate);
}
```

---

## Anti-Patterns

- Putting business logic in repository methods
- Using `findAll()` without pagination for large datasets
- Returning entities directly to controllers (use DTOs)
- N+1 queries (use `JOIN FETCH` or projections)
- Raw SQL when JPQL would work
