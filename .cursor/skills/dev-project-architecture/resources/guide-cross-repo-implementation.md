# Unified Cross-Repository Implementation Guide

Step-by-step guide for implementing features that span both `procurement-web` (Angular frontend) and `procurement-api` (Spring Boot backend). In this unified workspace, one agent executes the entire flow across both repositories.

## Unified Execution Model

The agent operates across both directories in a single session—unified execution, not separate contexts.

- **One Agent**: You are responsible for both frontend and backend implementation.
- **Two Repositories**: Navigate between `procurement-web/` and `procurement-api/` as needed.
- **Path Qualification**: To avoid ambiguity (since both have `src/`), always use fully qualified paths in your reasoning and plan:
  - `procurement-web/src/app/...`
  - `procurement-api/src/main/...`

## The Code-First Workflow

We use a **Code-First approach**. Backend DTO records and Springdoc controller annotations define the API contract, and both sides implement against that runtime-generated contract.

```
1. Define Backend Contract Code (DTO record + controller annotations)
       │
2. Generate OpenAPI via Springdoc (`/v3/api-docs`)
       │
3. Frontend Model Sync (hand-written models aligned to DTO/controller changes)
       │
4. Integration & Verification
       │
5. Unified Commit (Both repos)
```

## Step-by-Step Execution

### Step 1: Define the Backend Contract

Create or update backend DTO records and controller annotations in `procurement-api/`. This code is the single source of truth for the feature contract.

- Add or update DTO records under `src/main/java/doa/procurement/workflow/<domain>/dto/`.
- Annotate endpoints with `@Operation`, `@ApiResponse`, and `@Tag`.
- Apply Bean Validation to DTO fields and `@Valid` to `@RequestBody`.

### Step 2: Verify Contract Output

Run the backend and verify `/v3/api-docs` reflects the updated DTO/controller contract accurately.

### Step 3: Implement the Feature (Frontend & Backend)

Implement the frontend components and backend logic. Since you are in a unified workspace, you can develop both sides in parallel.

- **Frontend**: Build UI components in `procurement-web/` using hand-written feature models aligned to backend DTO/controller shapes.
- **Backend**: Implement controllers, DTOs, and services in `procurement-api/` with Springdoc annotations kept accurate.

### Step 4: Verify Backend

Verify the server-side implementation:

```bash
# From procurement-api/
./gradlew test
```

### Step 5: Integrate and Verify Frontend

Ensure the frontend correctly communicates with the real backend and all tests pass:

```bash
# From procurement-web/
npm test
```

### Step 6: Unified Commit

Once both sides are tested and verified, commit the changes. Since these are separate git repositories, you will need to commit in each.

```bash
# Commit frontend
cd procurement-web && git add . && git commit -m "feat: implement X frontend"

# Commit backend
cd procurement-api && git add . && git commit -m "feat: implement X backend"
```

## Troubleshooting

### Path Ambiguity
If you find yourself confused about which `src/` folder you are in, run `pwd`. Always specify the repository prefix when discussing files: "I will now edit `procurement-api/src/main/java/...`".

### Contract Mismatch
If contract behavior needs to change during implementation:
1. Update DTO records and/or controller annotations in `procurement-api/`.
2. Verify the generated spec at `/v3/api-docs`.
3. Update frontend hand-written feature models and implementation to match.

## Cross-References

- [checklist-api-implementation.md](checklist-api-implementation.md) - Implementation checklist
- [reference-api-endpoints.md](reference-api-endpoints.md) - Existing endpoints
- [guide-openapi-setup.md](guide-openapi-setup.md) - Type generation details
