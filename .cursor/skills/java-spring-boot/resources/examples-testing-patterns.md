# Examples: Testing Patterns

JUnit 5, AssertJ, and Mockito patterns for Spring Boot testing.

---

## Test Class Structure

```java
/**
 * Unit tests for ProjectService.
 */
class ProjectServiceTest {
    
    @Mock
    private ProjectRepository projectRepository;
    
    @Mock
    private UserLookup userLookup;
    
    @InjectMocks
    private ProjectService projectService;
    
    @BeforeEach
    void setUp() {
        MockitoAnnotations.openMocks(this);
    }
    
    @Test
    void testGetActiveProjects_returnsProjectsForUserAgency() {
        // Arrange
        String userId = "user123"; // Lowercase userId matches normalization requirements. In production, Okta may send mixed-case which is normalized.
        UserInfo user = UserInfo.builder().agencyId("AGY001").build();
        List<Project> projects = List.of(
            Project.builder().id(1L).name("Project A").build(),
            Project.builder().id(2L).name("Project B").build()
        );
        
        when(userLookup.getUser(userId)).thenReturn(user);
        when(projectRepository.findByAgencyIdAndIsActiveTrue("AGY001")).thenReturn(projects);
        
        // Act
        List<ProjectDTO> result = projectService.getActiveProjects(userId);
        
        // Assert
        assertThat(result)
            .isNotNull()
            .hasSize(2);
        assertThat(result.getFirst().name()).isEqualTo("Project A");
        
        verify(userLookup).getUser(userId);
        verify(projectRepository).findByAgencyIdAndIsActiveTrue("AGY001");
    }
}
```

---

## Spring Boot Integration Test

```java
/**
 * Integration tests for WorkflowService with full Spring context.
 */
@SpringBootTest
@ActiveProfiles("test")
class WorkflowServiceIntegrationTest {
    
    @Autowired
    private WorkflowService workflowService;
    
    @Autowired
    private WorkflowRepository workflowRepository;
    
    @MockitoBean
    private UserLookup userLookup;
    
    @BeforeEach
    void setUp() {
        workflowRepository.deleteAll();
    }
    
    @Test
    void testSubmitForApproval_updatesStatusAndCreatesAuditLog() {
        // Arrange
        Workflow workflow = workflowRepository.save(
            Workflow.builder()
                .status(WorkflowStatus.DRAFT)
                .amount(50000)
                .build()
        );
        
        when(userLookup.getUser("submitter")).thenReturn(
            UserInfo.builder().userId("submitter").displayName("John Doe").build()
        );
        
        // Act
        Workflow result = workflowService.submitForApproval(workflow.getId(), "submitter");
        
        // Assert
        assertThat(result.getStatus()).isEqualTo(WorkflowStatus.PENDING_APPROVAL);
        assertThat(result.getSubmittedBy()).isEqualTo("submitter");
        assertThat(result.getSubmittedDate()).isNotNull();
    }
}
```

---

## Repository Test with Test Database

```java
/**
 * Repository tests using H2 in-memory database.
 */
@DataJpaTest
@ActiveProfiles("test")
class ProjectRepositoryTest {
    
    @Autowired
    private ProjectRepository projectRepository;
    
    @Autowired
    private TestEntityManager entityManager;
    
    @Test
    void testFindByAgencyIdAndIsActiveTrue_returnsOnlyActiveProjects() {
        // Arrange
        Agency agency = entityManager.persist(
            Agency.builder().agencyId("AGY001").name("Test Agency").build()
        );
        
        entityManager.persist(Project.builder()
            .name("Active Project")
            .agency(agency)
            .isActive(true)
            .build());
        
        entityManager.persist(Project.builder()
            .name("Inactive Project")
            .agency(agency)
            .isActive(false)
            .build());
        
        entityManager.flush();
        
        // Act
        List<Project> result = projectRepository.findByAgencyIdAndIsActiveTrue("AGY001");
        
        // Assert
        assertThat(result)
            .hasSize(1)
            .extracting(Project::getName)
            .containsExactly("Active Project");
    }
}
```

---

## Controller Test with MockMvc

```java
/**
 * Controller tests using MockMvc.
 */
@WebMvcTest(ProjectController.class)
class ProjectControllerTest {
    
    @Autowired
    private MockMvc mockMvc;
    
    @MockitoBean
    private ProjectService projectService;
    
    @Autowired
    private ObjectMapper objectMapper;
    
    @Test
    void testGetAllProjects_returns200WithProjects() throws Exception {
        // Arrange
        List<ProjectDTO> projects = List.of(
            new ProjectDTO(1L, "Project A", ProjectStatus.ACTIVE, "Agency 1"),
            new ProjectDTO(2L, "Project B", ProjectStatus.DRAFT, "Agency 1")
        );
        when(projectService.getAllProjects()).thenReturn(projects);
        
        // Act & Assert
        mockMvc.perform(get("/api/v1/projects")
                .contentType(MediaType.APPLICATION_JSON))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$", hasSize(2)))
            .andExpect(jsonPath("$[0].name").value("Project A"))
            .andExpect(jsonPath("$[1].name").value("Project B"));
    }
    
    @Test
    void testCreateProject_returns201WithLocation() throws Exception {
        // Arrange
        CreateProjectDTO request = new CreateProjectDTO("New Project", "Description", "AGY001");
        ProjectDTO created = new ProjectDTO(1L, "New Project", ProjectStatus.DRAFT, "Agency 1");
        
        when(projectService.createProject(any(CreateProjectDTO.class))).thenReturn(created);
        
        // Act & Assert
        mockMvc.perform(post("/api/v1/projects")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
            .andExpect(status().isCreated())
            .andExpect(header().string("Location", "/api/v1/projects/1"))
            .andExpect(jsonPath("$.name").value("New Project"));
    }
    
    @Test
    void testCreateProject_returns400ForInvalidInput() throws Exception {
        // Arrange - name too short
        CreateProjectDTO request = new CreateProjectDTO("AB", null, "AGY001");
        
        // Act & Assert
        mockMvc.perform(post("/api/v1/projects")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
            .andExpect(status().isBadRequest());
    }
}
```

---

## AssertJ Assertion Patterns

```java
// Basic assertions
assertThat(result).isNotNull();
assertThat(result.getName()).isEqualTo("Expected");
assertThat(result.getAmount()).isGreaterThan(0);

// Collection assertions
assertThat(list)
    .isNotEmpty()
    .hasSize(3)
    .contains(item1, item2)
    .doesNotContain(item3);

// Extracting properties
assertThat(projects)
    .extracting(Project::getName)
    .containsExactly("A", "B", "C");

// Exception assertions (for guard clauses / invariants)
assertThatThrownBy(() -> service.process(null))
    .isInstanceOf(IllegalArgumentException.class)
    .hasMessage("Input cannot be null");

// Result-state assertion (for business outcomes)
ApprovalResult result = service.approveWorkflow(workflowId, approverId);
assertThat(result.status()).isEqualTo(ApprovalStatus.INVALID_STATE);
assertThat(result.reason()).contains("not pending");

// Chained assertions
assertThat(workflow)
    .isNotNull()
    .satisfies(w -> {
        assertThat(w.getStatus()).isEqualTo(WorkflowStatus.APPROVED);
        assertThat(w.getApprovedDate()).isNotNull();
    });
```

---

## Mockito Patterns

```java
// Basic stubbing
when(repository.findById(1L)).thenReturn(Optional.of(entity));
when(repository.findById(999L)).thenReturn(Optional.empty());

// Argument matchers
when(repository.save(any(Project.class))).thenAnswer(invocation -> {
    Project p = invocation.getArgument(0);
    p.setId(1L);
    return p;
});

// Verification
verify(repository).save(any(Project.class));
verify(repository, times(2)).findById(anyLong());
verify(repository, never()).delete(any());

// Argument capture
ArgumentCaptor<AuditLog> captor = ArgumentCaptor.forClass(AuditLog.class);
verify(auditLogRepository).save(captor.capture());
assertThat(captor.getValue().getAction()).isEqualTo("CREATE");
```

---

## Test Configuration

`src/test/resources/application-test.yml`:

```yaml
spring:
  datasource:
    url: jdbc:h2:mem:testdb
    driver-class-name: org.h2.Driver
  jpa:
    hibernate:
      ddl-auto: create-drop
    show-sql: true
```

---

## Test Naming Conventions

| Pattern | Example |
|---------|---------|
| `test{Method}_{scenario}` | `testGetProject_returnsNotFoundForInvalidId` |
| `test{Method}_{expectedResult}` | `testSubmit_updatesStatusToPending` |
| `{method}_when{Condition}_shouldThrowException` | `getProject_whenNotFound_shouldThrowException` |
| `{method}_when{Condition}_shouldReturn{Result}Result` | `approveWorkflow_whenInvalidState_shouldReturnInvalidStateResult` |

---

## Anti-Patterns

- Testing private methods directly
- Mocking the class under test
- Tests that depend on execution order
- Ignoring exception types in `assertThatThrownBy`
- Not verifying mock interactions when side effects matter
- Using `@Autowired` for beans under test in unit tests (use `@InjectMocks`)
