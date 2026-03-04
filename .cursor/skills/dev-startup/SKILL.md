---
name: dev-startup
description: "Provides local development environment startup and shutdown via dev-stack.py. Works across Angular/Java and Python/SvelteKit stacks. Use when starting dev servers, launching the application stack, or troubleshooting service startup. Complements environment skill's dev-stack.py status (diagnostic-only). DO NOT use for CI/CD or production deployment."
---

<ANCHORSKILL-DEV-STARTUP>

# Dev Startup

## The Port-in-Use Trap

A port check alone can't distinguish a healthy service from a crashed process holding a socket. A stale `gradlew` on port 8080 looks identical to a running API. This is why the default behavior is **reconcile** — classify each service's state before deciding what to do.

## Reconciler Model (Default)

| State | Action |
|---|---|
| Healthy + owned by us | **Keep** — skip with "healthy" message |
| Unhealthy + owned by us | **Restart** — stop then start |
| Port held by foreign process | **Fail** — rich diagnostics (PID, cmdline, cwd) |
| Not running | **Start** from scratch |

This is the default behavior of `dev-stack.py`. Use `--dry-run` to preview without acting.

## Service Stack

- **PostgreSQL** — container `procurement-postgres` on port `5432`
- **Spring Boot API** — `gradlew bootRun` on port `8080`
- **Angular Frontend** — `npm start` (ng serve) on port `4200`

Dependency chain: DB → API → Frontend (DB failure blocks API startup).

## Script Reference

### dev-stack.py

Unified command for managing the development stack.

`uv run dev-stack.py {start,stop,status} [flags]`

#### Subcommands

- **start**: Start local services with reconciliation and readiness checks.
- **stop**: Stop local services gracefully in reverse dependency order.
- **status**: Check health of running services.

#### Key Flags

| Flag | Purpose |
|-----|---------|
| `--fresh` | Stop all first, then start clean |
| `--force` | Bypass safety checks and force action |
| `--format` | Output format (markdown, json, text) |
| `--check-health` | Perform HTTP health checks on services |
| `--dry-run` | Print planned actions without executing |

## Quick Reference

- Container runtime: prefers `podman`, falls back to `docker`
- Container name: `procurement-postgres`
- Image: `docker.io/library/postgres:16-alpine`
- Default DB credentials: `procurement` / `dev_password` / `procurement_workflow`

## Troubleshooting

- **Flyway checksum mismatch**: Run backend migration repair/reset before restart.
- **Foreign process on port**: Use `--dry-run` to see PID/cmdline, kill manually, then retry.
- **Container already exists**: Script starts existing stopped containers; remove manually only for a clean database.
- **Diagnose without changes**: Use `uv run dev-stack.py status` to see what the reconciler would do.

## Universal-API Stack

### Services

- **Backend (FastAPI)**: Python via Anaconda on port `8000`
- **Frontend (SvelteKit)**: Node 20 LTS on port `4173`

### Startup Commands

- **Backend**: `conda activate Universal-API && uvicorn src.backend.web_api:app --host 0.0.0.0 --port 8000`
- **Frontend**: `cd src/frontend && npm run dev -- --host 0.0.0.0 --port 4173`
- **Full stack**: Backend on 8000, Frontend on 4173, `VITE_API_URL=http://localhost:8000`

## Cross-Reference

- [Cross-References](resources/cross-references.md)
- For diagnostics-only status checks, use `uv run .cursor/skills/dev-startup/scripts/dev-stack.py status`.

</ANCHORSKILL-DEV-STARTUP>
