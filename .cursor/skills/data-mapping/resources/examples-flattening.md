# Examples: Flattening

JSON to DataFrame column flattening patterns.

---

## Pattern

Nested JSON fields are flattened using component prefixes and underscores:
- `field.subfield` → `prefix_field_subfield`
- Arrays/complex types → JSON strings or flatten

---

## Project Implementation

### Input JSON

```python
{
  "name": "My API",
  "auth": {
    "type": "api_key",
    "key_ref": "$ENV{KEY}"
  }
}
```

### Output DataFrame Columns

```python
entity_label = "My API"
authconfig_type = "api_key"
authconfig_key_ref = "$ENV{KEY}"
```

---

## Flattening Rules

| Input Structure | Output Column | Type |
|-----------------|---------------|------|
| Top-level string | `prefix_field` | pl.Utf8 |
| Nested object | `prefix_parent_child` | pl.Utf8 |
| Boolean | `prefix_field` | pl.Boolean |
| Number | `prefix_field` | pl.Int64 or pl.Float64 |
| Array (simple) | `prefix_field` | JSON string |
| Array (complex) | Flatten each or JSON | Depends |

---

## Type Consistency

| Polars Type | Use For |
|-------------|---------|
| `pl.Utf8` | Strings, URLs, references |
| `pl.Boolean` | Flags, toggles |
| `pl.Int64` | Integers, counts |
| `pl.Float64` | Decimals, percentages |
