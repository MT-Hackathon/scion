---
name: postgresql-design
description: "Governs PostgreSQL schema design and investigation: FK indexing mandates, JSONB column patterns, query optimization, migration strategy, and DB-first debugging. Use when designing database schemas, writing Flyway migrations, optimizing queries, or diagnosing data issues. DO NOT use for JPA entity mapping (see java-spring-boot) or data contract validation (see data-contracts)."
---

<ANCHORSKILL-POSTGRESQL-DESIGN>

# PostgreSQL Design & Investigation

## 1. Primary Mandates
- **Identity**: `BIGINT GENERATED ALWAYS AS IDENTITY`. Avoid legacy `SERIAL`.
- **Public IDs**: Use `UUID` for public-facing identifiers.
- **Timestamps**: Always `TIMESTAMPTZ` (`OffsetDateTime` in Java).
- **FK Indexing**: **MANDATORY**. Add B-tree indexes to all Foreign Keys.
- **Identity-Authority FK**: Authorization tables (`user_roles`, memberships, delegations) MUST have FK to their parent identity table (`users`). No orphaned grants.
- **Normalization**: User IDs lowercased via `CHECK (user_id = LOWER(user_id))`.

## 2. Constraints & Types
- **Money**: Use `NUMERIC(19,4)` (`BigDecimal`). Never use `FLOAT` or `MONEY`.
- **Enums**: `@Enumerated(EnumType.STRING)`. Values MUST match OpenAPI spec exactly.
- **JSONB**: Use for semi-structured data. Always add GIN indexes.

## 3. Investigation (Territory Principle)
Establish baseline state by querying the DB. Establishment of fact precedes establishing cause.
- **Query Tool**: `uv run .cursor/skills/postgresql-design/scripts/db_query.py "SQL"`
- **Schema**: `\d+ table_name` for actual DDL verification.
- **Explain**: Use `EXPLAIN ANALYZE` for performance investigation.

## 4. Migrations (Flyway)
- **Source of Truth**: SQL scripts define the schema, not JPA entities.
- **Hibernate**: `ddl-auto: validate` in production.
- **Constraint Naming**: Explicitly name PK/FK/UK/CK for debugging.

## 5. Resources & Scripts
- [Blueprint: Index Audit SQL](blueprints/index-audit.sql)
- [scripts/schema-diff.py](scripts/schema-diff.py) — Compare JPA entities to DB and emit Flyway SQL.
- [scripts/seed-data.py](scripts/seed-data.py) — Generate realistic INSERT statements for dev seeding.
- [Cross-References](resources/cross-references.md)

</ANCHORSKILL-POSTGRESQL-DESIGN>
