from __future__ import annotations

import pytest

from scripts.seed.database_dataset import DATABASE_TABLE_COLUMNS
from scripts.seed.postgres import normalize_postgres_url, write_dataset_to_postgres
from scripts.seed.upsert_engine import UpsertEngine


def test_normalize_postgres_url_accepts_common_drivers():
    assert normalize_postgres_url("postgresql+asyncpg://db") == "postgresql://db"
    assert normalize_postgres_url("postgresql+psycopg://db") == "postgresql://db"
    assert normalize_postgres_url("postgres://db") == "postgres://db"


def test_normalize_postgres_url_rejects_non_postgresql_scheme():
    with pytest.raises(ValueError, match="PostgreSQL"):
        normalize_postgres_url("sqlite:///seed.db")


def test_writer_preflights_schema_then_executes_upsert(monkeypatch):
    from scripts.seed import postgres

    class Cursor:
        def __init__(self):
            self.executed = []
            self.results = []

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, statement, params=None):
            self.executed.append((statement, params))
            if statement.lstrip().startswith("SELECT"):
                self.results = [("users", column) for column in DATABASE_TABLE_COLUMNS["users"]]

        def fetchall(self):
            return self.results

    class Connection:
        def __init__(self):
            self.test_cursor = Cursor()

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def cursor(self):
            return self.test_cursor

    connection = Connection()
    monkeypatch.setattr(postgres.psycopg, "connect", lambda _dsn: connection)
    dataset = {"users": [{"user_id": "seed-user-1", "full_name": "Seed User", "role": "ADMIN"}]}

    result = write_dataset_to_postgres(dataset, "postgresql://db", engine=UpsertEngine())

    assert result == {"users": 1}
    assert connection.test_cursor.executed[0][0].lstrip().startswith("SELECT")
    assert "INSERT INTO users" in connection.test_cursor.executed[1][0]
    assert "ON CONFLICT (user_id) DO UPDATE" in connection.test_cursor.executed[1][0]


def test_writer_rejects_missing_target_table_before_writing(monkeypatch):
    from scripts.seed import postgres

    class Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, _statement, _params=None):
            pass

        def fetchall(self):
            return []

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def cursor(self):
            return Cursor()

    monkeypatch.setattr(postgres.psycopg, "connect", lambda _dsn: Connection())
    dataset = {"users": [{"user_id": "seed-user-1", "full_name": "Seed User", "role": "ADMIN"}]}

    with pytest.raises(RuntimeError, match="falta la tabla users"):
        write_dataset_to_postgres(dataset, "postgresql://db", engine=UpsertEngine())
