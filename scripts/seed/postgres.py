from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import psycopg

from .database_dataset import DATABASE_TABLE_COLUMNS
from .upsert_engine import TOPOLOGICAL_TABLE_ORDER, UpsertEngine


def normalize_postgres_url(database_url: str) -> str:
    """Converts SQLAlchemy PostgreSQL driver URLs to psycopg-compatible URLs."""
    for driver in ("postgresql+asyncpg://", "postgresql+psycopg://", "postgresql+psycopg2://"):
        if database_url.startswith(driver):
            return "postgresql://" + database_url.removeprefix(driver)
    if database_url.startswith(("postgresql://", "postgres://")):
        return database_url
    raise ValueError("AGROSENSE_DATABASE_URL debe usar un esquema PostgreSQL compatible.")


def _validate_schema(cursor: Any, dataset: Mapping[str, list[dict[str, Any]]]) -> None:
    tables = [table for table, rows in dataset.items() if rows]
    cursor.execute(
        """
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = ANY(%s)
        """,
        (tables,),
    )
    available: dict[str, set[str]] = {}
    for table_name, column_name in cursor.fetchall():
        available.setdefault(table_name, set()).add(column_name)

    issues: list[str] = []
    for table in tables:
        expected_columns = set(DATABASE_TABLE_COLUMNS[table])
        actual_columns = available.get(table)
        if actual_columns is None:
            issues.append(f"falta la tabla {table}")
            continue
        missing_columns = expected_columns - actual_columns
        if missing_columns:
            issues.append(f"{table}: faltan columnas {', '.join(sorted(missing_columns))}")

    if issues:
        raise RuntimeError(
            "El esquema PostgreSQL no coincide con las migraciones de AgroSense: "
            + "; ".join(issues)
            + ". Aplique las migraciones antes de ejecutar el seed."
        )


def write_dataset_to_postgres(
    dataset: dict[str, list[dict[str, Any]]],
    database_url: str,
    *,
    engine: UpsertEngine,
    reset_database: bool = False,
) -> dict[str, int]:
    """Validates the target schema and applies generated UPSERT statements atomically."""
    dsn = normalize_postgres_url(database_url)
    statements_by_table = engine.build_all_upsert_statements(dataset)
    tables = [table for table in TOPOLOGICAL_TABLE_ORDER if dataset.get(table)]

    with psycopg.connect(dsn) as connection:
        with connection.cursor() as cursor:
            _validate_schema(cursor, dataset)
            if reset_database:
                cursor.execute(
                    "TRUNCATE TABLE " + ", ".join(reversed(tables)) + " RESTART IDENTITY"
                )
            for table in tables:
                for statement in statements_by_table.get(table, []):
                    cursor.execute(statement)

    return {table: len(dataset[table]) for table in tables}
