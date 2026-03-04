# Registry Reference

State container registry patterns for registry.mt.gov.

## Registry URL

Base path for AHS images:

```text
registry.mt.gov/enterprise/doa/sitsd/atsb/ahs/
```

## Authentication

Store credentials in `.env` (see [security skill](../../security/SKILL.md)):

```bash
# .env (gitignored)
REGISTRY_USER=your-username
REGISTRY_TOKEN=your-token
```

Login before push/pull:

```bash
source .env  # or use python-dotenv in scripts
podman login registry.mt.gov -u $REGISTRY_USER -p $REGISTRY_TOKEN
```

## Base Images

Use state-approved base images:

```dockerfile
# Nginx base (from existing Dockerfile)
FROM registry.mt.gov/enterprise/doa/sitsd/atsb/ahs/base-images/nginx:latest

# Node base (for builds)
FROM docker.io/library/node:22-alpine AS builder
```

## Tagging Convention

```bash
# Format: registry/namespace/app:version
podman tag myapp registry.mt.gov/enterprise/doa/sitsd/atsb/ahs/apps/procurement-web:1.2.3
podman push registry.mt.gov/enterprise/doa/sitsd/atsb/ahs/apps/procurement-web:1.2.3
```

## CI/CD Push

Handled by external GitLab templates. Do not push manually in prod pipelines.
