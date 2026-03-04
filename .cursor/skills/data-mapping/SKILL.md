---
name: data-mapping
description: "Governs component prefix rules and mapping principles for pipeline node data to DataFrame columns. Use when understanding how node component types map to data schema columns in pipeline construction. DO NOT use for pipeline canvas mechanics (see ui-canvas) or data contract validation (see data-contracts)."
---

<ANCHORSKILL-DATA-MAPPING>

# Data Mapping Principles Rule

## Table of Contents & Resources
- [Core Concepts](#core-concepts)
- [Blueprint: Node Flattener](blueprints/node-flattener.py)
- [Reference: Column Prefixes](resources/reference-column-prefixes.md)
- [Examples: Flattening](resources/examples-flattening.md)
- [Checklist: Data Mapping](resources/checklist-data-mapping.md)
- [Cross-References](resources/cross-references.md)

## Core Concepts

### Contract (MANDATED)
Node JSON → DataFrame columns with **component prefixes**  
Common columns: `entity_id`, `entity_type`, `entity_label`, `configurationstate_is_configured`

### Prefixes
`api_source`: `endpointconfig_` + `authconfig_`, `hashconfig_`, `encryptconfig_`  
`database_target`: `databaseconfig_`  
`transform`: `transformconfig_`

### Flattening & Types
Nested: `field.subfield` → `prefix_field_subfield`; Arrays/complex → JSON strings or flatten; Consistent types (`pl.Utf8`, `pl.Boolean`)

### Prohibited
Nested dicts/lists in columns, inconsistent prefixes, non-snake_case, in-place mutation

</ANCHORSKILL-DATA-MAPPING>
