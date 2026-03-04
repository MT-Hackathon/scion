# Cross-References: postgresql-design

## Adjacent Skills

| Skill | Relationship |
|---|---|
| [java-spring-boot](../../java-spring-boot/SKILL.md) | JPA entity mapping and `@Enumerated`/`@Column` annotations that must align with the schema mandates here. Start here for DB schema; go there for ORM layer. |
| [data-contracts](../../data-contracts/SKILL.md) | API response types must match column types defined in schema (e.g. `NUMERIC(19,4)` → `BigDecimal`, `TIMESTAMPTZ` → `OffsetDateTime`). |
| [api-design](../../api-design/SKILL.md) | Enum values in OpenAPI spec must match exactly what is stored in `@Enumerated(EnumType.STRING)` columns. |
| [error-architecture](../../error-architecture/SKILL.md) | DB constraint violations (FK, UK, NOT NULL) surface as specific exception types that the error architecture layer must handle explicitly. |
| [integration-testing](../../integration-testing/SKILL.md) | Integration tests against real PostgreSQL (via TestContainers) are the verification gate for schema mandates and FK index coverage. |
