# Reference: Column Prefixes

Component prefix lookup table for DataFrame columns.

---

## Prefix Table

| Component Type | Prefix | Example Columns |
|----------------|--------|-----------------|
| API Source - Endpoint | `endpointconfig_` | `endpointconfig_url`, `endpointconfig_method` |
| API Source - Auth | `authconfig_` | `authconfig_auth_type`, `authconfig_api_key_ref` |
| API Source - Hash | `hashconfig_` | `hashconfig_algorithm` |
| API Source - Encrypt | `encryptconfig_` | `encryptconfig_key_ref` |
| Database Target | `databaseconfig_` | `databaseconfig_connection_string`, `databaseconfig_table_name` |
| Transform | `transformconfig_` | `transformconfig_operation`, `transformconfig_filter` |

---

## Common Columns

All entities include these standard columns:

| Column | Type | Description |
|--------|------|-------------|
| `entity_id` | pl.Utf8 | Unique identifier |
| `entity_type` | pl.Utf8 | Node type (e.g., `apiSource`) |
| `entity_label` | pl.Utf8 | Display name |
| `configurationstate_is_configured` | pl.Boolean | Configuration complete flag |

---

## Column Examples

```python
# API Source
endpointconfig_url
authconfig_auth_type
hashconfig_algorithm

# Database Target
databaseconfig_connection_string
databaseconfig_table_name

# Transform
transformconfig_operation
transformconfig_filter
```
