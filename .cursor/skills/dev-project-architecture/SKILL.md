---
name: dev-project-architecture
description: "Governs cross-project development architecture: workspace layouts, multi-repo and monorepo patterns, worktree configuration, and IDE project setup across sibling repositories. Use when structuring a new project, configuring workspace roots, or managing multi-repo layout decisions. DO NOT use for container setup (see container) or dev server startup (see dev-startup)."
---

<ANCHORSKILL-DEV-PROJECT-ARCHITECTURE>

# Dev Project Architecture (Unified)

## 1. Unified Workspace
The `procurement-web` and `procurement-api` repositories are managed as a single integrated project.
- **Context**: Agents operate across both directories.
- **API Boundary**: Backend DTO records and Springdoc-annotated controllers are the contract source; frontend models stay synchronized to that contract.

## 2. Code-First Unified Development
Backend contract code enables simultaneous, type-safe implementation across the stack.
```
Define DTO + Controller Annotations → Springdoc `/v3/api-docs` → Align hand-written frontend models → Implement E2E → Unified Commit
```
- **Web Types**: Hand-written models in `procurement-web/src/app/features/**/models/` kept in sync with DTO/controller contract changes
- **API Implementation**: Standalone controllers, DTO records, and services (no generated interfaces)

## 3. Remote Sync Pattern
Workaround for VPN firewalls and multi-platform sync.
- **origin**: CDO GitLab (Primary)
- **github**: GitHub (Secondary/CI)
- **state**: State GitLab (git.mt.gov)

## 4. Universal-API Architecture

### Monorepo Layout
- **Backend**: `src/backend/` — Python/FastAPI, ECS pattern
- **Frontend**: `src/frontend/` — SvelteKit 5 (Node 20 LTS)
- **Governance**: `.cursor/` — shared rules, skills, and agents

### Development Workflow
```
Define Pydantic models + FastAPI routes → Align SvelteKit types → Implement E2E → Commit
```
- **Backend types**: Pydantic models in `src/backend/`
- **Frontend types**: TypeScript interfaces in `src/frontend/src/lib/types/`
- **Environment**: Anaconda (`Universal-API` env) for Python, npm for SvelteKit

## 5. Resources & Scripts

### Resources
- [Guide: Cross-Repo Implementation](resources/guide-cross-repo-implementation.md)
- [Guide: OpenAPI Setup](resources/guide-openapi-setup.md)
- [Guide: Local Mocking](resources/guide-local-mocking.md)
- [Checklist: Cross-Repo Task](resources/checklist-cross-repo-task.md)
- [Checklist: API Implementation](resources/checklist-api-implementation.md)
- [Checklist: VPN Sync](resources/checklist-vpn-sync.md)
- [Reference: API Endpoints](resources/reference-api-endpoints.md)
- [Template: API Contract](resources/template-api-contract.md)

### Scripts
- **remote-sync.py configure**: Setup remotes for the project.
- **remote-sync.py push**: Push to all remotes in one command.
- **remote-sync.py status**: Verify commit parity across remotes.
- **mock-server.py** (api-design skill): Boot a Prism mock server from an exported OpenAPI specification.

### Cross-References
- [Cross-References](resources/cross-references.md)

</ANCHORSKILL-DEV-PROJECT-ARCHITECTURE>
