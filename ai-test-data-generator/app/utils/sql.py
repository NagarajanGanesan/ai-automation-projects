"""SQL seed-data helpers.

Turns generated rows into a :class:`DatabaseSeedData` object containing both the
structured rows and ready-to-run ``INSERT`` statements. Values are rendered as
SQL literals with single quotes doubled to avoid trivial breakage; this targets
seeding test databases, not untrusted input, but the escaping keeps generated
strings (e.g. names with apostrophes) syntactically valid.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.models.schemas import DatabaseSeedData


def _sql_literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return repr(value)
    text = str(value).replace("'", "''")
    return f"'{text}'"


def _ordered_columns(rows: List[Dict[str, Any]]) -> List[str]:
    """Union of keys across rows, preserving first-seen order."""
    columns: List[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    return columns


def build_seed_data(table: str, rows: List[Dict[str, Any]]) -> DatabaseSeedData:
    """Build :class:`DatabaseSeedData` (rows + INSERT statements) for ``rows``."""
    columns = _ordered_columns(rows)
    statements: List[str] = []
    col_list = ", ".join(columns)
    for row in rows:
        values = ", ".join(_sql_literal(row.get(col)) for col in columns)
        statements.append(f"INSERT INTO {table} ({col_list}) VALUES ({values});")
    return DatabaseSeedData(table=table, columns=columns, rows=rows, sql=statements)
