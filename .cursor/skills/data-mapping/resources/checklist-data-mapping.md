# Checklist: Data Mapping

Data mapping validation checklist.

---

## Prefixes

- [ ] Correct component prefix used
- [ ] Nested fields flattened with underscores
- [ ] Common columns present (entity_id, entity_type, entity_label)

## Types

- [ ] Consistent Polars types (pl.Utf8, pl.Boolean, pl.Int64)
- [ ] No nested dicts/lists in columns
- [ ] Complex types serialized to JSON strings

## Prohibited

- [ ] No inconsistent prefixes
- [ ] No non-snake_case column names
- [ ] No in-place mutations
