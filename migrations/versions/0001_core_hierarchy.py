from __future__ import annotations

from collections.abc import Sequence

from migrations.sql_loader import run_sql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    run_sql("0001_core_hierarchy.sql")


def downgrade() -> None:
    run_sql("0001_core_hierarchy.down.sql")
