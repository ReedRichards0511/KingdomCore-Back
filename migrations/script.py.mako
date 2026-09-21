"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

El SQL vive en migrations/sql/. Esta revision solo lo ejecuta.
"""

from __future__ import annotations

from collections.abc import Sequence

from migrations.sql_loader import run_sql

revision: str = ${repr(up_revision)}
down_revision: str | None = ${repr(down_revision)}
branch_labels: str | Sequence[str] | None = ${repr(branch_labels)}
depends_on: str | Sequence[str] | None = ${repr(depends_on)}


def upgrade() -> None:
    run_sql("${up_revision}_<nombre>.sql")


def downgrade() -> None:
    run_sql("${up_revision}_<nombre>.down.sql")
