#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = ["faker"]
# ///
"""
seed-data.py
Generate realistic PostgreSQL INSERT statements for common procurement tables
(users, procurement_request, approvals) using Faker.

Usage:
  ./seed-data.py --tables users,procurement_request --count 50 --output seed.sql
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import random
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

try:
    from faker import Faker
except ImportError:  # pragma: no cover
    Faker = None  # type: ignore


DEFAULT_TABLES = ["users", "procurement_request", "approvals"]


def sql_value(val) -> str:
    if val is None:
        return "NULL"
    if isinstance(val, bool):
        return "TRUE" if val else "FALSE"
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, (dt.date, dt.datetime)):
        return f"'{val.isoformat()}'"
    text = str(val).replace("'", "''")
    return f"'{text}'"


def generate_users(fake: Faker, count: int) -> List[Dict[str, object]]:
    rows = []
    roles = ["REQUESTER", "APPROVER", "ADMIN"]
    for i in range(1, count + 1):
        name = fake.name()
        email = fake.email().lower()
        rows.append(
            {
                "id": i,
                "full_name": name,
                "email": email,
                "role": random.choice(roles),
                "created_at": dt.datetime.utcnow(),
                "active": True,
            }
        )
    return rows


def generate_requests(fake: Faker, count: int, user_ids: Sequence[int]) -> List[Dict[str, object]]:
    rows = []
    statuses = ["DRAFT", "SUBMITTED", "APPROVED", "REJECTED"]
    for i in range(1, count + 1):
        requester = random.choice(user_ids) if user_ids else None
        rows.append(
            {
                "id": i,
                "requester_id": requester,
                "title": fake.sentence(nb_words=6),
                "amount": round(random.uniform(500, 25000), 2),
                "status": random.choices(statuses, weights=[0.2, 0.4, 0.3, 0.1])[0],
                "needed_by": dt.date.today() + dt.timedelta(days=random.randint(5, 45)),
                "created_at": dt.datetime.utcnow(),
            }
        )
    return rows


def generate_approvals(fake: Faker, count: int, user_ids: Sequence[int], request_ids: Sequence[int]) -> List[Dict[str, object]]:
    rows = []
    decisions = ["APPROVED", "REJECTED", "PENDING"]
    for i in range(1, count + 1):
        request_id = random.choice(request_ids) if request_ids else None
        approver_id = random.choice(user_ids) if user_ids else None
        decided = random.choice([True, False, False])
        status = random.choice(decisions) if decided else "PENDING"
        decided_at = dt.datetime.utcnow() if decided else None
        rows.append(
            {
                "id": i,
                "request_id": request_id,
                "approver_id": approver_id,
                "decision": status,
                "comment": fake.sentence(nb_words=10),
                "decided_at": decided_at,
                "created_at": dt.datetime.utcnow(),
            }
        )
    return rows


def build_insert(table: str, rows: List[Dict[str, object]]) -> List[str]:
    if not rows:
        return []
    columns = list(rows[0].keys())
    statements = []
    for row in rows:
        values = ", ".join(sql_value(row[c]) for c in columns)
        columns_sql = ", ".join(columns)
        statements.append(f"INSERT INTO {table} ({columns_sql}) VALUES ({values});")
    return statements


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate PostgreSQL seed INSERT statements.")
    parser.add_argument("--tables", default="all", help="Comma-separated tables to seed (or 'all').")
    parser.add_argument("--count", type=int, default=100, help="Rows per table.")
    parser.add_argument("--output", default=None, help="File to write SQL to (stdout if omitted).")
    parser.add_argument("--locale", default="en_US", help="Faker locale (default: en_US).")
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    if Faker is None:
        print("Faker is required. Install with: pip install Faker", file=sys.stderr)
        return 1

    fake = Faker(args.locale)
    table_arg = [t.strip() for t in args.tables.split(",") if t.strip()]
    targets = DEFAULT_TABLES if table_arg == ["all"] else table_arg

    user_rows: List[Dict[str, object]] = []
    request_rows: List[Dict[str, object]] = []
    approval_rows: List[Dict[str, object]] = []
    statements: List[str] = []

    if "users" in targets:
        user_rows = generate_users(fake, args.count)
        statements.extend(build_insert("users", user_rows))

    if "procurement_request" in targets:
        request_rows = generate_requests(fake, args.count, [r["id"] for r in user_rows])
        statements.extend(build_insert("procurement_request", request_rows))

    if "approvals" in targets:
        approval_rows = generate_approvals(
            fake,
            args.count,
            [r["id"] for r in user_rows],
            [r["id"] for r in request_rows],
        )
        statements.extend(build_insert("approvals", approval_rows))

    header = [
        "-- seed-data.py",
        f"-- locale: {args.locale}",
        f"-- rows per table: {args.count}",
    ]
    output = "\n".join(header + statements)

    if args.output:
        Path(args.output).write_text(output)
    else:
        print(output)

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
