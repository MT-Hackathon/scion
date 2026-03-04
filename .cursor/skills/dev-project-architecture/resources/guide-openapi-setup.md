# Code-First Springdoc Setup Guide

Instructions for API contract development between `procurement-api` (backend) and `procurement-web` (frontend) using a code-first workflow.

## Overview

This project uses **Code-First API Development**:

1. **Backend Contract Source**: Java DTO records and controller annotations define the API contract.
2. **Spec Generation**: Springdoc auto-generates OpenAPI at `/v3/api-docs` from running code.
3. **Frontend Sync**: Frontend maintains hand-written models in `src/app/features/**/models/` aligned with DTO/controller changes.
4. **End-to-End Verification**: Work is complete only when backend and frontend align in runtime behavior.

```
Backend DTO + Controller Annotations
              |
              v
       Springdoc /v3/api-docs
              |
              v
 Frontend hand-written models
              |
              v
   Integrated implementation
```

## Backend Setup (`procurement-api`)

### Step 1: Ensure Springdoc Dependency

In `build.gradle.kts`:

```kotlin
dependencies {
    // ... existing dependencies
    implementation("org.springdoc:springdoc-openapi-starter-webmvc-ui:2.8.0")
}
```

### Step 2: Verify Springdoc Endpoint Settings

In `application.yml`:

```yaml
springdoc:
  api-docs:
    path: /v3/api-docs
  swagger-ui:
    path: /swagger-ui.html
    enabled: true
```

### Step 3: Create a DTO Record

Define request/response payloads as records in a domain DTO package such as
`src/main/java/doa/procurement/workflow/<domain>/dto/`.

```java
package doa.procurement.workflow.request.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.util.UUID;

@Schema(name = "CreateRequestRequest", description = "Payload to create a procurement request")
public record CreateRequestRequest(
    @Schema(description = "Owning purchasing agency ID", format = "uuid")
    @NotNull UUID purchasingAgencyId,
    @Schema(description = "Request item name")
    @NotBlank String itemName,
    @Schema(description = "Detailed description of the requested purchase")
    @NotBlank String description
) {}
```

### Step 4: Add a Controller Endpoint with Springdoc Annotations

```java
package doa.procurement.workflow.request;

import doa.procurement.workflow.request.dto.CreateRequestRequest;
import doa.procurement.workflow.request.dto.RequestSummary;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/requests")
@Tag(name = "Requests", description = "Procurement request endpoints")
public class RequestController {

    @PostMapping
    @Operation(summary = "Create a procurement request")
    @ApiResponse(
        responseCode = "201",
        description = "Request created",
        content = @Content(schema = @Schema(implementation = RequestSummary.class))
    )
    @ApiResponse(responseCode = "400", description = "Validation failed")
    public ResponseEntity<RequestSummary> createRequest(
        @Valid @RequestBody CreateRequestRequest request
    ) {
        // implementation omitted
        return ResponseEntity.status(201).build();
    }
}
```

### Step 5: Verify Generated Spec

Run the backend and verify:

- Swagger UI: `http://localhost:8080/swagger-ui.html`
- OpenAPI JSON: `http://localhost:8080/v3/api-docs`

## Frontend Sync (`procurement-web`)

### Option A: Hand-Written Feature Models

Create and maintain TypeScript models in feature directories:

- `src/app/features/<feature>/models/*.ts`

Keep field names, required/optional status, and enum/string semantics aligned with backend DTOs.

### Option B: Model Alignment Validation

After DTO/controller updates, verify frontend model files under `src/app/features/**/models/` still match:

- property names and casing
- required vs optional fields
- string vs enum semantics documented in backend `@Schema`

## Recommended Delivery Flow

1. Add/update DTO record with `@Schema` and Bean Validation constraints.
2. Add/update `@RestController` endpoint with `@Operation` and `@ApiResponse`.
3. Verify `/v3/api-docs` reflects the endpoint and schema accurately.
4. Update frontend hand-written feature models to match DTO/controller changes.
5. Implement service/UI behavior and verify end-to-end integration.

## Troubleshooting

### Missing Endpoint in `/v3/api-docs`

- Confirm controller has `@RestController` and mapped method annotation.
- Confirm class is in a scanned package under application root.
- Confirm security/config does not block `/v3/api-docs`.

### Validation Rules Not Enforced

- Ensure `@RequestBody` is paired with `@Valid`.
- Ensure constraints are on DTO fields (`@NotNull`, `@Size`, etc.).

### Frontend Types Drift from Backend

- Compare DTO/controller response shapes against feature model definitions.
- Update hand-written models in `src/app/features/**/models/` immediately.
- Resolve drift immediately; do not defer contract mismatches.

## Cross-References

- [guide-cross-repo-implementation.md](guide-cross-repo-implementation.md) - Unified implementation flow
- [checklist-api-implementation.md](checklist-api-implementation.md) - Execution checklist
- [reference-api-endpoints.md](reference-api-endpoints.md) - Existing endpoints
