---
name: container
description: "Governs Docker and Podman container workflows for building, running, and debugging. Use when working with Dockerfiles, container images, registries, or CI/CD. Covers rootless Podman for state infrastructure. DO NOT use for Kubernetes or cloud orchestration."
---

<ANCHORSKILL-CONTAINER>

# Container

## Table of Contents & Resources

- [Core Concepts](#core-concepts)
- [Blueprint: Multi-Stage Dockerfile](blueprints/multi-stage.dockerfile)
- [Blueprint: Compose Hardening](blueprints/compose-hardening.yaml)
- [Reference: Podman](resources/reference-podman.md)
- [Reference: Docker](resources/reference-docker.md)
- [Reference: Registry](resources/reference-registry.md)
- [Examples: Dockerfile](resources/examples-dockerfile.md)
- [Cross-References](resources/cross-references.md)

## Core Concepts

### Tool Selection (MANDATED)

- **Podman**: State CI/CD (`AHSPODMAN` runners), rootless containers, production
- **Docker**: Local development with Docker Desktop, BuildKit builds

### Common Commands

Both tools share identical CLI:

| Command | Purpose |
|---------|---------|
| `build -t name .` | Build image from Dockerfile |
| `run -d --name x image` | Run container detached |
| `exec -it x bash` | Shell into running container |
| `logs -f x` | Stream container logs |
| `ps -a` | List all containers |
| `stop x && rm x` | Stop and remove container |
| `images` | List local images |
| `pull registry/image:tag` | Pull from registry |
| `push registry/image:tag` | Push to registry |

### Build Arguments

Pass environment-specific config at build time:

```bash
podman build --build-arg BUILD_ENV=nonprod -t myapp .
```

### Registry Authentication

See [security skill](../security/SKILL.md) for credential storage. Login pattern:

```bash
podman login registry.mt.gov -u $REGISTRY_USER -p $REGISTRY_TOKEN
```

### Container Security (MANDATED)

Production containers must follow defense-in-depth hardening:

**Non-Root Execution**:
- All production Dockerfiles MUST include a `USER` directive
- Create a dedicated application user: `RUN addgroup -S appgroup && adduser -S appuser -G appgroup`
- Set ownership before switching: `RUN chown -R appuser:appgroup /app`
- Switch user: `USER appuser`

**No Secrets in Image Layers**:
- Never `COPY .env` into the image
- Never use `ENV SECRET_KEY=value` or `ARG` for secrets
- Secrets are injected at runtime via environment variables or secret managers
- Image layers are permanent and inspectable - secrets baked in are secrets leaked

**Minimal Base Images**:
- Use alpine or slim variants (`node:22-alpine`, `eclipse-temurin:25-jre-alpine`)
- Multi-stage builds to exclude build tools from final image
- No package managers or shells in production images when possible

**Compose Hardening**: Apply the [compose-hardening blueprint](blueprints/compose-hardening.yaml) — resource limits, read-only filesystem, `tmpfs`, and `no-new-privileges`.

**Health Checks**:
- All services must define health checks in Compose or Dockerfile
- Use endpoint-based checks for application containers, TCP checks for databases
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8080/actuator/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### Prohibited Patterns

- Running containers as root when rootless available
- Hardcoded registry URLs (use variables)
- Missing `.dockerignore` (bloats image)
- Storing registry credentials in Dockerfile
- Using `latest` tag in production

</ANCHORSKILL-CONTAINER>
