# BLUEPRINT: node-flattener.py
# STRUCTURAL: flatten_node_to_row, COMPONENT_PREFIXES, COMMON_COLUMNS
# ILLUSTRATIVE: api_source block — replace with actual component types and their config keys

from __future__ import annotations

import json
from typing import Any

import polars as pl

# STRUCTURAL: Map every component type to its config blocks (block_key → column prefix).
#             This is the single source of truth — derive nothing else from it.
COMPONENT_PREFIXES: dict[str, dict[str, str]] = {
    "api_source": {                           # ILLUSTRATIVE: component type name
        "endpointconfig": "endpointconfig_",  # ILLUSTRATIVE: block key → prefix
        "authconfig": "authconfig_",
        "hashconfig": "hashconfig_",
        "encryptconfig": "encryptconfig_",
    },
    "database_target": {
        "databaseconfig": "databaseconfig_",
    },
    "transform": {
        "transformconfig": "transformconfig_",
    },
    # ILLUSTRATIVE: "your_component": {"yourconfig": "yourconfig_"},
}

# STRUCTURAL: All entities carry these columns; never omit or rename them.
COMMON_COLUMNS: dict[str, pl.DataType] = {
    "entity_id": pl.Utf8,
    "entity_type": pl.Utf8,
    "entity_label": pl.Utf8,
    "configurationstate_is_configured": pl.Boolean,
}


def flatten_node_to_row(node: dict[str, Any]) -> dict[str, Any]:
    """Flatten a pipeline node dict to a single DataFrame-compatible row.

    Nested fields are mapped via component prefix: ``field.subfield`` →
    ``{prefix}field_subfield``.  Arrays and complex objects are serialized
    to JSON strings.  Type coercion follows COMMON_COLUMNS and the Polars
    type table in reference-column-prefixes.md.
    """
    entity_type: str = node["entity_type"]  # guard: must be present
    # STRUCTURAL: unknown entity_type raises — fail fast, never silently drop.
    if entity_type not in COMPONENT_PREFIXES:
        raise ValueError(f"Unknown entity_type: {entity_type!r}")

    row: dict[str, Any] = {
        "entity_id": node["entity_id"],
        "entity_type": entity_type,
        "entity_label": node.get("entity_label", ""),
        "configurationstate_is_configured": node.get("configurationstate_is_configured", False),
    }

    # STRUCTURAL: flatten only the config blocks registered for this entity_type.
    for block_key, prefix in COMPONENT_PREFIXES[entity_type].items():
        block = node.get(block_key, {})
        if not isinstance(block, dict):
            continue
        for field, value in block.items():
            column = f"{prefix}{field}"
            row[column] = json.dumps(value) if isinstance(value, (dict, list)) else value

    return row


def nodes_to_dataframe(nodes: list[dict[str, Any]]) -> pl.DataFrame:
    """Convert a list of flattened node dicts to a Polars DataFrame.

    Missing columns across rows are null-filled.  Common column types
    are enforced; all other columns default to pl.Utf8.
    """
    rows = [flatten_node_to_row(n) for n in nodes]
    df = pl.from_dicts(rows, infer_schema_length=len(rows))

    # STRUCTURAL: enforce mandatory column types; do not relax these casts.
    for col, dtype in COMMON_COLUMNS.items():
        if col in df.columns:
            df = df.with_columns(pl.col(col).cast(dtype))

    return df
