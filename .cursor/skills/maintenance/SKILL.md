---
name: maintenance
description: "Governs application maintenance and operations: health monitoring, performance optimization, dependency management, backup procedures, and incident response. Use when diagnosing production issues, optimizing performance, updating dependencies, managing backups, or troubleshooting operational problems. DO NOT use for CI/CD pipeline management (see ci-pipeline), container setup (see container), or cross-layer test debugging (see testing-debugging)."
---

<ANCHORSKILL-MAINTENANCE>

# Maintenance & Operations

## Contents

- [Health Monitoring](#health-monitoring)
- [Performance Optimization](#performance-optimization)
- [Dependency Management](#dependency-management)
- [Backup Strategy](#backup-strategy)
- [Debugging Production Issues](#debugging-production-issues)
- [Security Maintenance](#security-maintenance)
- [Scaling Considerations](#scaling-considerations)
- [Incident Response](#incident-response)
- [Cross-References](#cross-references)

## Health Monitoring

### Spring Boot Actuator (Primary)

The application exposes health via Spring Boot Actuator:

- `/actuator/health` — Aggregated health status (database, disk, custom indicators)
- `/actuator/info` — Application metadata (version, git info)
- `/actuator/metrics` — Micrometer metrics (JVM, HTTP, custom)
- `/actuator/loggers` — Runtime log level management

**Security**: `/actuator/health` and `/actuator/info` are public; all other actuator endpoints require ADMIN role.

### System Health Dashboard (Admin)

Monitor these metrics:

| Category | Key Metrics |
|----------|------------|
| Database | Connection pool usage, slow queries, table sizes |
| JVM | Heap usage, GC frequency, thread count |
| HTTP | Request rate, error rate (4xx/5xx), average response time |
| Disk | Upload directory size, log file sizes |
| External | Okta SSO availability, SCIM endpoint status |

### External Monitoring

| Tool | Purpose |
|------|---------|
| Uptime check | Ping `/actuator/health` every 60s |
| Prometheus + Grafana | Metrics collection and dashboards (Micrometer export) |
| Sentry / ELK | Error tracking and log aggregation |
| APM | Application performance monitoring |

## Performance Optimization

### Backend Performance

1. **Database query optimization**
   - Add indexes on columns used in WHERE, JOIN, and ORDER BY (FK indexes are mandatory)
   - Use `EXPLAIN ANALYZE` to identify slow queries
   - Paginate all list endpoints (never return unbounded results)
   - Use `JOIN FETCH` for relationships accessed in the same transaction (N+1 prevention)

2. **Caching strategy**
   - Use Spring Cache (`@Cacheable`) with Caffeine for local caches
   - Set appropriate TTLs (5 min for dashboard aggregations, 1 hour for config/display names)
   - Invalidate cache on writes (`@CacheEvict`)
   - Configuration data (display names, agency list) is a strong caching candidate

3. **Connection management**
   - HikariCP connection pool: monitor via `/actuator/metrics/hikaricp.connections`
   - Default pool size: 10 connections; tune based on load
   - Slow query threshold: log queries exceeding 1000ms

### Frontend Performance

1. **Bundle optimization**
   - Use lazy loading (`loadComponent`) for feature routes
   - Optimize images with `NgOptimizedImage` directive
   - Ensure production builds use AOT compilation and tree-shaking

2. **Data loading**
   - Use signals for component state (automatic change detection, no unnecessary re-renders)
   - Implement pagination for all list views
   - Debounce search/filter inputs (300-500ms)

3. **Caching**
   - Set appropriate `Cache-Control` headers for static assets via nginx
   - Angular service worker for offline support (if needed)

## Dependency Management

### Regular Update Schedule

| Frequency | What | How |
|-----------|------|-----|
| Weekly | Security advisories | `./gradlew dependencyCheckAnalyze`, `npm audit` |
| Monthly | Patch versions | `./gradlew dependencyUpdates`, `npm update` |
| Quarterly | Minor versions | Review changelogs, test thoroughly |
| Annually | Major versions | Plan migration, allocate time for breaking changes |

### Backend Updates (Gradle)

```bash
# Check for outdated dependencies
./gradlew dependencyUpdates

# Check for security vulnerabilities (OWASP dependency-check)
./gradlew dependencyCheckAnalyze

# Update a specific dependency in build.gradle, then:
./gradlew test --no-daemon
./gradlew checkstyleMain spotbugsMain --no-daemon
```

### Frontend Updates (npm)

```bash
# Check for outdated packages
npm outdated

# Check for security vulnerabilities
npm audit

# Update packages
npm update                      # Minor and patch updates
npx npm-check-updates -u       # Major updates (review carefully)
npm install

# Test after updates
npm run build && npm run lint && npm run test:ci
```

## Backup Strategy

### Database Backups

```bash
# Manual backup (from Docker host)
docker compose exec db pg_dump -U procurement procurement_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore from backup
docker compose exec -T db psql -U procurement procurement_db < backup_20260212.sql

# Compressed backup
docker compose exec -T db pg_dump -U procurement procurement_db | gzip > /backups/db_$(date +\%Y\%m\%d).sql.gz
```

### Backup Checklist

- [ ] Daily automated database backups
- [ ] Backup uploaded attachments/files
- [ ] Test restore procedure monthly
- [ ] Store backups off-site (cloud storage or separate server)
- [ ] Retention policy: 7 daily, 4 weekly, 12 monthly
- [ ] Monitor backup job success/failure

## Debugging Production Issues

### Common Investigation Steps

1. **Check health**: `curl /actuator/health`
2. **Review logs**: `docker compose logs -f backend --since 1h`
3. **Check database**: Connection count, lock contention, slow queries — see [DB Investigation Reference](resources/reference-db-investigation.md)
4. **Check JVM**: Heap usage, GC activity via `/actuator/metrics`
5. **Check disk**: Upload directory size, log rotation
6. **Check external services**: Okta SSO status, SCIM endpoint health

## Security Maintenance

### Regular Security Tasks

| Frequency | Task |
|-----------|------|
| Weekly | Review dependency security advisories (`./gradlew dependencyCheckAnalyze`, `npm audit`) |
| Monthly | Review and rotate service account credentials |
| Quarterly | Review user access, deactivate stale accounts |
| Quarterly | Review audit logs for suspicious activity |
| Annually | Full security review (see [Security Audit Checklist](../security/resources/checklist-security-audit.md)) |

## Scaling Considerations

### When to Scale

| Symptom | Likely Bottleneck | Action |
|---------|-------------------|--------|
| Slow API responses | Backend CPU/memory | Scale backend instances, increase JVM heap |
| Connection pool exhaustion | Database connections | Tune HikariCP pool size, optimize query duration |
| Slow queries | Database | Add indexes, optimize queries, or upgrade DB |
| High memory usage | JVM heap or caching | Review cache strategy, check for memory leaks via heap dump |
| Frontend bundle too large | JavaScript payload | Lazy load routes, audit bundle with `source-map-explorer` |

## Incident Response

Use the [Incident Report Template](resources/template-incident-report.md) to document any P1/P2/P3 incident. Fill in all fields immediately — timeline reconstruction degrades after 24 hours.

## Cross-References

- [Security Skill](../security/SKILL.md) — Auth, credential rotation, security configuration
- [Container Skill](../container/SKILL.md) — Docker compose operations referenced in backup/debugging steps
- [PostgreSQL Design Skill](../postgresql-design/SKILL.md) — Index mandates, query optimization patterns
- [CI Pipeline Skill](../ci-pipeline/SKILL.md) — Pipeline-level dependency update automation

</ANCHORSKILL-MAINTENANCE>
