# Docker Reference

Local development patterns for Docker Desktop environments.

## Daemon Architecture

Docker requires background daemon. Start with:

```bash
# macOS/Windows: Docker Desktop manages daemon
# Linux: systemctl start docker
```

## BuildKit (Default in Docker 23+)

Enhanced build performance and caching:

```bash
DOCKER_BUILDKIT=1 docker build -t myapp .
```

BuildKit features:

- Parallel stage execution
- Better cache invalidation
- Secret mounts (no secrets in image layers)

## Secret Mounts (BuildKit)

Mount secrets at build time without baking into image:

```dockerfile
# syntax=docker/dockerfile:1
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc npm ci
```

```bash
docker build --secret id=npmrc,src=.npmrc -t myapp .
```

## Docker Desktop Resource Limits

Configure in Docker Desktop > Settings > Resources:

- CPUs: 4+ for Angular builds
- Memory: 8GB+ recommended
- Disk: 64GB+ for image cache

## Docker Compose

Multi-container local development:

```bash
docker compose up -d
docker compose logs -f app
docker compose exec app bash
docker compose down -v  # -v removes volumes
```
