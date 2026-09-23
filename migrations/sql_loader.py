from __future__ import annotations

from pathlib import Path

from alembic import op

SQL_DIR = Path(__file__).resolve().parent / "sql"


def read_sql(filename: str) -> str:
    path = SQL_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"No existe la migracion SQL: {path}")
    return path.read_text(encoding="utf-8")


def run_sql(filename: str) -> None:
    op.execute(read_sql(filename))
