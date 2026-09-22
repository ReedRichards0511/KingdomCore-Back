from __future__ import annotations

from collections.abc import Sequence

from migrations.sql_loader import run_sql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    run_sql("0003_seed_hierarchy.sql")


def downgrade() -> None:
    run_sql("0003_seed_hierarchy.down.sql")
