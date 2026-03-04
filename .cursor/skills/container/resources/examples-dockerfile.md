# Dockerfile Examples

Patterns from this project's Dockerfile.

## Multi-Stage Angular Build

```dockerfile
# Stage 1: Build
FROM docker.io/library/node:22-alpine AS builder

COPY . /app
WORKDIR /app

# npm ci with lock file prevents silent dependency drift
RUN npm ci

# No default forces explicit injection — prevents silent misconfiguration
ARG BUILD_ENV
RUN npm run build:${BUILD_ENV}

# Stage 2: Serve
FROM registry.mt.gov/enterprise/doa/sitsd/atsb/ahs/base-images/nginx:latest

# Output path: /app/dist/{project-name}/browser where project-name matches angular.json
COPY --from=builder /app/dist/app/browser /usr/share/nginx/html
# Base image runs nginx as non-root (uid 101). For generic nginx image: add USER nginx

CMD ["nginx", "-g", "daemon off;"]
```

## Key Patterns

| Pattern | Purpose |
|---------|---------|
| `AS builder` | Named stage for multi-stage builds |
| `npm ci` | Deterministic install from lock file |
| `ARG BUILD_ENV` | Build-time variable injection |
| `COPY --from=builder` | Copy artifacts from previous stage |
| `USER` directive | Non-root execution for production security |
| `/app/dist/app/browser` | Angular output path (from angular.json) |

## .dockerignore

Create `.dockerignore` to exclude build bloat:

```text
node_modules
dist
.git
.angular
coverage
*.log
.env
```

## Build Commands

```bash
# Nonprod
podman build --build-arg BUILD_ENV=nonprod -t procurement-web:dev .

# Prod
podman build --build-arg BUILD_ENV=prod -t procurement-web:latest .
```
