#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
schema-diff.py
Compare JPA entities (procurement-api) to a live PostgreSQL schema and emit
Flyway-ready SQL suggestions to close gaps (create/alter/index).

Usage:
  ./schema-diff.py [--db-url URL] [--output PATH] [--dry-run]
                   [--schema-json PATH]

Inputs:
- JPA entities are parsed from ../procurement-api/src by default (override with
  PROCUREMENT_API_ROOT).
- Database schema is read from --db-url (falls back to env or compose.yaml).
- Alternatively provide --schema-json containing information_schema-like rows.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

try:
    import psycopg  # type: ignore
except ImportError:  # pragma: no cover
    psycopg = None


PROJECT_ROOT = Path(__file__).resolve().parents[4]
API_ROOT = Path(os.getenv("PROCUREMENT_API_ROOT", PROJECT_ROOT.parent / "procurement-api"))
DEFAULT_COMPOSE = API_ROOT / "compose.yaml"


# ----------------------------- Helpers ------------------------------------- #


def snake_case(name: str) -> str:
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def default_db_url() -> str:
    env_url = (
        os.getenv("SPRING_DATASOURCE_URL")
        or os.getenv("DATABASE_URL")
        or os.getenv("DB_URL")
    )
    if env_url:
        return env_url.replace("jdbc:", "")

    if DEFAULT_COMPOSE.exists():
        content = DEFAULT_COMPOSE.read_text()
        db = re.search(r"POSTGRES_DB:\s*([^\s]+)", content)
        user = re.search(r"POSTGRES_USER:\s*([^\s]+)", content)
        pwd = re.search(r"POSTGRES_PASSWORD:\s*\${[^:]+:-([^\}]+)\}", content) or re.search(
            r"POSTGRES_PASSWORD:\s*([^\s]+)", content
        )
        return f"postgresql://{(user.group(1) if user else 'postgres')}:{(pwd.group(1) if pwd else 'postgres')}@localhost:5432/{(db.group(1) if db else 'postgres')}"

    return "postgresql://postgres:postgres@localhost:5432/postgres"


# ----------------------------- Entity Parsing ------------------------------ #


JAVA_TO_PG = {
    "String": "text",
    "Long": "bigint",
    "long": "bigint",
    "Integer": "integer",
    "int": "integer",
    "BigDecimal": "numeric(19,4)",
    "OffsetDateTime": "timestamptz",
    "Instant": "timestamptz",
    "LocalDate": "date",
    "Boolean": "boolean",
    "boolean": "boolean",
    "UUID": "uuid",
}


@dataclass
class ColumnDef:
    name: str
    pg_type: str
    nullable: bool
    default: Optional[str] = None
    is_fk: bool = False


def java_to_pg(java_type: str, annotations: str) -> str:
    base = JAVA_TO_PG.get(java_type, "text")
    precision = re.search(r"precision\s*=\s*(\d+)", annotations)
    scale = re.search(r"scale\s*=\s*(\d+)", annotations)
    length = re.search(r"length\s*=\s*(\d+)", annotations)

    if precision and scale:
        return f"numeric({precision.group(1)},{scale.group(1)})"
    if length and base == "text":
        return f"varchar({length.group(1)})"
    return base


def parse_entities(api_root: Path) -> Dict[str, Dict[str, ColumnDef]]:
    entities: Dict[str, Dict[str, ColumnDef]] = {}
    src_root = api_root / "src"
    if not src_root.exists():
        return entities

    for path in src_root.rglob("*.java"):
        text = path.read_text()
        if "@Entity" not in text:
            continue

        for match in re.finditer(r"@Entity[\s\S]*?class\s+(\w+)", text):
            class_name = match.group(1)
            preamble = text[: match.start()]
            table_match = re.search(r"@Table\s*\(\s*name\s*=\s*\"([^\"]+)\"", text[match.start() : match.end()])
            table = table_match.group(1) if table_match else snake_case(class_name)

            entity_block = text[match.end() :]
            next_entity = entity_block.find("@Entity")
            if next_entity != -1:
                entity_block = entity_block[:next_entity]

            columns: Dict[str, ColumnDef] = {}
            annotations_buffer: List[str] = []
            for line in entity_block.splitlines():
                stripped = line.strip()
                if stripped.startswith("@"):
                    annotations_buffer.append(stripped)
                    continue

                field_match = re.match(r"private\s+([\w\.<>]+)\s+(\w+);", stripped)
                if not field_match:
                    continue

                java_type, field_name = field_match.groups()
                annotations = " ".join(annotations_buffer)
                annotations_buffer = []

                col_match = re.search(r"name\s*=\s*\"([^\"]+)\"", annotations)
                col_name = col_match.group(1) if col_match else snake_case(field_name)
                nullable_match = re.search(r"nullable\s*=\s*(false|true)", annotations)
                nullable = False if nullable_match and nullable_match.group(1) == "false" else True
                is_fk = "@JoinColumn" in annotations or "@ManyToOne" in annotations

                columns[col_name] = ColumnDef(
                    name=col_name,
                    pg_type=java_to_pg(java_type, annotations),
                    nullable=nullable if not is_fk else False,
                    default=None,
                    is_fk=is_fk,
                )

            entities[table] = columns

    return entities


# ----------------------------- DB Introspection ---------------------------- #


def load_schema_from_db(db_url: str) -> Dict[str, Dict[str, Any]]:
    if psycopg is None:
        raise RuntimeError("psycopg is required to introspect the database (pip install psycopg[binary]).")

    parsed: Dict[str, Dict[str, Any]] = {}
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name,
                       column_name,
                       data_type,
                       is_nullable,
                       COALESCE(numeric_precision, character_maximum_length) AS precision,
                       numeric_scale,
                       column_default
                  FROM information_schema.columns
                 WHERE table_schema = 'public'
                 ORDER BY table_name, ordinal_position
                """
            )
            for row in cur.fetchall():
                table, col, dtype, nullable, precision, scale, default = row
                def _identity() -> str:
                    return dtype

                type_formatters = {
                    "numeric": lambda: f"numeric({int(precision)},{int(scale or 0)})" if precision else dtype,
                    "character varying": lambda: f"varchar({int(precision)})" if precision else dtype,
                    "character": lambda: f"varchar({int(precision)})" if precision else dtype,
                    "timestamp with time zone": lambda: "timestamptz",
                }
                fmt_type = type_formatters.get(dtype, _identity)()
                parsed.setdefault(table, {})[col] = {
                    "type": fmt_type,
                    "nullable": nullable == "YES",
                    "default": default,
                }

            cur.execute(
                """
                SELECT
                    t.relname AS table_name,
                    i.relname AS index_name,
                    array_to_string(array_agg(a.attname ORDER BY a.attnum), ',') AS columns
                FROM pg_class t
                JOIN pg_index ix ON t.oid = ix.indrelid
                JOIN pg_class i ON i.oid = ix.indexrelid
                JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
                JOIN pg_namespace n ON n.oid = t.relnamespace
                WHERE n.nspname = 'public' AND NOT ix.indisprimary
                GROUP BY t.relname, i.relname
                """
            )
            for table, _, cols in cur.fetchall():
                parsed.setdefault(table, {}).setdefault("_indexes", set()).add(cols)

    return parsed


def load_schema_from_json(path: Path) -> Dict[str, Dict[str, Dict[str, str]]]:
    with path.open() as fh:
        payload = json.load(fh)
    return payload if isinstance(payload, dict) else {}


# ----------------------------- Diff & SQL ---------------------------------- #


def compare(entity_schema: Dict[str, Dict[str, ColumnDef]], db_schema: Dict[str, Dict[str, Dict[str, str]]]) -> List[str]:
    statements: List[str] = []
    for table, cols in entity_schema.items():
        actual = db_schema.get(table, {})
        if not actual:
            col_sql = []
            for col in cols.values():
                col_sql.append(render_column(col))
            statements.append(
                f"-- Table missing in DB: {table}\nCREATE TABLE {table} (\n    {',\\n    '.join(col_sql)}\n);"
            )
            fk_indexes = [col.name for col in cols.values() if col.is_fk]
            statements.extend([f"CREATE INDEX idx_{table}_{c} ON {table} ({c});" for c in fk_indexes])
            continue

        for col_name, col_def in cols.items():
            if col_name not in actual:
                statements.append(f"ALTER TABLE {table} ADD COLUMN {render_column(col_def)};")
                if col_def.is_fk:
                    statements.append(f"CREATE INDEX idx_{table}_{col_name} ON {table} ({col_name});")
                continue

            db_col = actual[col_name]
            if normalize_type(col_def.pg_type) != normalize_type(db_col["type"]):
                statements.append(
                    f"-- Type mismatch (entity {col_def.pg_type} vs db {db_col['type']})\n"
                    f"ALTER TABLE {table} ALTER COLUMN {col_name} TYPE {col_def.pg_type};"
                )

            if col_def.nullable != db_col["nullable"]:
                action = "DROP NOT NULL" if col_def.nullable else "SET NOT NULL"
                statements.append(f"ALTER TABLE {table} ALTER COLUMN {col_name} {action};")

            if col_def.is_fk:
                indexes = actual.get("_indexes", set())
                if not any(col_name in idx for idx in indexes):
                    statements.append(f"-- Missing FK index\nCREATE INDEX idx_{table}_{col_name} ON {table} ({col_name});")

    return statements


def normalize_type(pg_type: str) -> str:
    return pg_type.replace(" ", "").lower()


def render_column(col: ColumnDef) -> str:
    nullable = "" if col.nullable else " NOT NULL"
    default = f" DEFAULT {col.default}" if col.default else ""
    return f"{col.name} {col.pg_type}{default}{nullable}"


# ----------------------------- CLI ----------------------------------------- #


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diff JPA entities against PostgreSQL schema and emit Flyway SQL.")
    parser.add_argument("--db-url", dest="db_url", default=None, help="Database URL (postgresql://...)")
    parser.add_argument("--output", dest="output", default=None, help="File to write SQL suggestions to")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", help="Only show SQL; never apply")
    parser.add_argument(
        "--schema-json",
        dest="schema_json",
        default=None,
        help="Path to pre-exported schema JSON (alternative to live DB introspection)",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    db_url = args.db_url or default_db_url()

    entities = parse_entities(API_ROOT)
    if not entities:
        print(f"No entities found under {API_ROOT}. Set PROCUREMENT_API_ROOT or add entities.", file=sys.stderr)
        return 1

    try:
        if args.schema_json:
            db_schema = load_schema_from_json(Path(args.schema_json))
        else:
            db_schema = load_schema_from_db(db_url)
    except Exception as exc:  # pragma: no cover - runtime connectivity errors
        print(f"Failed to introspect database: {exc}", file=sys.stderr)
        return 1

    statements = compare(entities, db_schema)
    header = [
        f"-- schema-diff.py (dry-run={args.dry_run})",
        f"-- db-url: {db_url}",
        f"-- entities: {API_ROOT}",
    ]

    if not statements:
        output = "\n".join(header + ["-- Schemas appear in sync. No actions suggested."])
    else:
        output = "\n".join(header + ["BEGIN;"] + statements + ["COMMIT;"])

    if args.output:
        Path(args.output).write_text(output)
    else:
        print(output)

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
