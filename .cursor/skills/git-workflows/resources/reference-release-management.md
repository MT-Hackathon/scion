# Reference: Release Management

Versioning, changelogs, pre-release checklists, and deployment procedures for the procurement system.

---

## Versioning Strategy

Use **Semantic Versioning** (SemVer): `MAJOR.MINOR.PATCH`

| Increment | When | Example |
|-----------|------|---------|
| MAJOR | Breaking API changes, major workflow overhauls | 1.0.0 -> 2.0.0 |
| MINOR | New features, non-breaking additions | 1.0.0 -> 1.1.0 |
| PATCH | Bug fixes, security patches, minor tweaks | 1.0.0 -> 1.0.1 |

### Version Locations

Update version in these files on each release:

- `procurement-api/build.gradle` — `version = '1.2.0'`
- `procurement-web/package.json` — `"version": "1.2.0"`
- Git tag — `v1.2.0`

---

## Changelog

Maintain `CHANGELOG.md` at each repository root:

```markdown
# Changelog

## [1.2.0] - 2026-02-15

### Added
- Parallel approval gates for IT Review and OBPP
- Attachment preview in request detail view

### Changed
- Improved dashboard loading performance
- Updated Angular Material to latest patch

### Fixed
- Fixed pagination offset on request list
- Corrected timezone display in audit logs

### Security
- Updated Spring Boot to address CVE-XXXX-YYYY

## [1.1.0] - 2026-01-20
...
```

Categories: **Added**, **Changed**, **Deprecated**, **Removed**, **Fixed**, **Security**

---

## Pre-Release Checklist

```markdown
## Release v{X.Y.Z} Checklist

### Code Quality
- [ ] All backend tests passing (`./gradlew test --no-daemon`)
- [ ] All frontend tests passing (`npm run test:ci`)
- [ ] Backend static analysis clean (`./gradlew checkstyleMain spotbugsMain --no-daemon`)
- [ ] Frontend lint clean (`npm run lint`)
- [ ] Frontend typecheck clean (`npx tsc --noEmit`)
- [ ] Code review completed for all MRs in this release
- [ ] No known security vulnerabilities (`./gradlew dependencyCheckAnalyze`, `npm audit`)

### Database
- [ ] All Flyway migrations tested (upgrade path verified)
- [ ] Migrations run cleanly on a fresh database
- [ ] Seed data updated if schema changed
- [ ] Backup strategy verified for production data

### Configuration
- [ ] `application.yml` / `application-*.yml` updated with any new properties
- [ ] No secrets committed to repository
- [ ] Docker images build successfully
- [ ] Environment parity verified (local matches container)

### Documentation
- [ ] CHANGELOG.md updated
- [ ] README.md updated if setup steps changed
- [ ] OpenAPI docs current (`/v3/api-docs` reflects latest DTOs and annotations)
- [ ] Requirements documents updated if behavior changed

### Deployment
- [ ] Health check endpoint responds correctly (`/actuator/health`)
- [ ] Database migrations run without errors in staging
- [ ] Rollback procedure tested and documented
- [ ] Monitoring configured for new features
```

---

## Git Workflow

### Branch Strategy

The project uses a multi-branch strategy with CDO GitLab as primary origin:

```
main (production)
  └── dev/next (integration)
        ├── dev/offline-sprint (offline work)
        ├── feat/<issue-id>-description
        ├── fix/<issue-id>-description
        └── release/v1.2.0
```

### Release Process

```bash
# 1. Create release branch from dev/next
git checkout dev/next
git pull origin dev/next
git checkout -b release/v1.2.0

# 2. Update version numbers
# Edit build.gradle, package.json

# 3. Update CHANGELOG.md
# Add all changes since last release

# 4. Final testing
cd procurement-api && ./gradlew test --no-daemon
cd ../procurement-web && npm run test:ci && npm run build

# 5. Merge to main
git checkout main
git merge release/v1.2.0
git tag -a v1.2.0 -m "Release v1.2.0"
git push origin main --tags

# 6. Merge back to dev/next
git checkout dev/next
git merge release/v1.2.0
git push origin dev/next

# 7. Sync to remotes
uv run git-sync.py mirror --source gitlab --target github
```

---

## Rollback Procedure

```bash
# 1. Identify the last good version
git log --oneline --tags

# 2. Deploy previous tag
git checkout v1.1.0
docker compose up --build -d

# 3. Rollback database if needed
# Review Flyway migration history: SELECT * FROM flyway_schema_history ORDER BY installed_rank DESC;
# Manual rollback SQL if Flyway undo not available

# 4. Verify health
curl http://localhost:8080/actuator/health
curl http://localhost:4200/
```

---

## Hotfix Process

```bash
# Branch from main (not dev/next)
git checkout main
git checkout -b hotfix/v1.2.1

# Fix the issue, test, update version and changelog

# Merge to both main AND dev/next
git checkout main && git merge hotfix/v1.2.1
git tag -a v1.2.1 -m "Hotfix v1.2.1"
git push origin main --tags

git checkout dev/next && git merge hotfix/v1.2.1
git push origin dev/next
```

---

## Deployment Sync to State GitLab

After a release is tagged and pushed to CDO GitLab origin:

```bash
# Push to state remote (requires VPN)
git push state main --tags

# Verify state pipeline
uv run git-pipeline.py list --provider state --limit 1
```

See [ci-pipeline skill](../../ci-pipeline/SKILL.md) for STATE GitLab troubleshooting.
