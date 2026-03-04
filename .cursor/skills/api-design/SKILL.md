---
name: api-design-principles
description: "Governs code-first API design for FastAPI and Spring Boot: Pydantic/DTO contracts, RFC 7807 error responses, OpenAPI annotations, request/response modeling, and schema design policies. Use when designing REST endpoints, authoring Pydantic or DTO contracts, or configuring Springdoc/FastAPI routers. DO NOT use for service layer patterns (see java-spring-boot) or integration testing (see integration-testing)."
---

<ANCHORSKILL-API-DESIGN-PRINCIPLES>

# API Design (Code-First)

> **Stack Coverage**: Principles §1–5 are stack-agnostic. §1–4 carry Spring Boot / Springdoc specifics. `blueprints/fastapi-router.py` and `blueprints/dto-contract.py` demonstrate FastAPI + Pydantic equivalents. See [Reference Implementations](resources/reference-implementations.md) for production source pointers.

## 1. API Source of Truth (Spring Boot)
Java code is the source of truth for the Spring Boot stack. DRIFT IS A FAILURE.
- **Location**: `procurement-api/src/main/java/doa/procurement/workflow/**/dto/` and Springdoc-annotated controllers.
- **Workflow**: Create or update DTO record (`@Schema` + Bean Validation) → annotate controller endpoint (`@Operation`, `@ApiResponse`, `@Tag`) → Springdoc auto-generates `/v3/api-docs` → update frontend hand-written models in `procurement-web/src/app/features/**/models/` to match DTO changes → implement.
- **Spec Generation**: `/v3/api-docs` is generated from running backend code, not hand-authored YAML.

## 2. Schema Design Policy
- **Prefer `type: string`**: For configurable/tenant-specific values (categories, status). Use `description` to list known values.
- **Restricted `enum`**: Only for fixed protocol-level values (e.g., `SortDirection`).
- **Display Names**: Server-driven via `/api/v1/config`. Never hardcode labels in frontend.
- **Agency Context**: All resources must include `originatingAgencyId` and `purchasingAgencyId` (UUIDs).

## 3. DTO Schema Management
To prevent contract drift and duplicated representations across domains:
- **Shared DTOs**: Reuse DTO records for shared domain concepts instead of redefining near-identical records.
- **Single Meaning per Type**: If two payloads carry different semantics, use distinct DTO names (e.g., `ApprovalRequestDetail` vs `RequestDetail`) even when fields overlap.
- **Annotation Accuracy**: Keep `@Schema` descriptions, examples, and required/nullable semantics synchronized with validation annotations.

## 4. Resource Patterns
- **URL**: Versioned `/api/v1/...`.
- **Normalization**: Database values MUST match DTO and API contract case exactly.
- **Naming**: PascalCase for Schemas, camelCase for properties.
- **Pagination**: Mandatory for collections (`page`, `size`, `sort`).

## 5. Error Handling (RFC 7807)
Standardize on **Problem Details** (`ProblemDetail` in Spring).
- **Required**: `type`, `title`, `status`, `detail`, `instance`.
- **MDC**: Trace IDs must be propagated to error responses.

## 6. Resources & Scripts
- [FastAPI Router Blueprint](blueprints/fastapi-router.py)
- [DTO Contract Blueprint](blueprints/dto-contract.py)
- [Reference Implementations](resources/reference-implementations.md)
- [Swagger UI Configuration](../dev-project-architecture/resources/guide-openapi-setup.md)
- [Example: Problem Details](../dev-project-architecture/resources/template-api-contract.md)
- **Frontend model alignment**: Keep hand-written frontend models synchronized with backend DTO/controller contract changes

</ANCHORSKILL-API-DESIGN-PRINCIPLES>
