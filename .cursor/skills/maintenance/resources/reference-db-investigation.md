# Database Investigation Reference

Diagnostic SQL queries for PostgreSQL. Run against the procurement database during incident response or performance investigation.

## Active Connections

```sql
SELECT count(*) FROM pg_stat_activity WHERE state = 'active';
```

## Long-Running Queries (> 5 seconds)

```sql
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE state = 'active' AND now() - pg_stat_activity.query_start > interval '5 seconds';
```

## Table Sizes

```sql
SELECT relname, pg_size_pretty(pg_total_relation_size(relid))
FROM pg_catalog.pg_statio_user_tables ORDER BY pg_total_relation_size(relid) DESC;
```

## Lock Contention

```sql
SELECT * FROM pg_locks WHERE NOT granted;
```

## Unused Indexes

```sql
SELECT schemaname, relname, indexrelname, idx_scan
FROM pg_stat_user_indexes WHERE idx_scan = 0 ORDER BY relname;
```

## Checklist: When Queries Are Slow

1. Run `EXPLAIN ANALYZE <slow query>` to inspect query plan
2. Check if FK indexes are missing on JOIN columns (see [postgresql-design skill](../../skills/postgresql-design/SKILL.md))
3. Check connection pool exhaustion via `/actuator/metrics/hikaricp.connections`
4. Look for N+1 patterns — use `JOIN FETCH` for relationships accessed in the same transaction
