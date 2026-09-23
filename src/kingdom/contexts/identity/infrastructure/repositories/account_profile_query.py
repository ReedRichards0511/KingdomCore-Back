from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from kingdom.contexts.identity.application.projections.account_profile import (
    AccountProfile,
    RoleView,
)

if TYPE_CHECKING:
    import asyncpg

    from kingdom.shared.domain.ports.unit_of_work import UnitOfWork


class PostgresAccountProfileQuery:
    def __init__(self, *, unit_of_work: UnitOfWork) -> None:
        self._uow = unit_of_work

    async def profile_of(self, account_id: UUID) -> AccountProfile | None:
        account_row: asyncpg.Record | None = await self._uow.connection.fetchrow(
            """
            SELECT ua.id AS account_id,
                   ua.must_change_password,
                   p.document_type,
                   p.document_number,
                   p.first_names,
                   p.paternal_surname,
                   p.maternal_surname,
                   p.contact_email
              FROM user_accounts ua
              JOIN persons p ON p.id = ua.person_id
             WHERE ua.id = $1
               AND ua.deleted_at IS NULL
               AND p.deleted_at IS NULL
            """,
            account_id,
        )
        if account_row is None:
            return None

        role_rows: list[asyncpg.Record] = await self._uow.connection.fetch(
            """
            SELECT ra.role, ra.scope_type, ra.scope_id,
                   COALESCE(pa.name, c.name, v.name, a.name) AS scope_name
              FROM role_assignments ra
              LEFT JOIN parishes     pa ON ra.scope_type = 'parish'      AND pa.id = ra.scope_id
              LEFT JOIN communities  c  ON ra.scope_type = 'community'   AND c.id  = ra.scope_id
              LEFT JOIN vicariates   v  ON ra.scope_type = 'vicariate'   AND v.id  = ra.scope_id
              LEFT JOIN archdioceses a  ON ra.scope_type = 'archdiocese' AND a.id  = ra.scope_id
             WHERE ra.user_account_id = $1
               AND ra.revoked_at IS NULL
               AND ra.deleted_at IS NULL
            """,
            account_id,
        )

        roles = tuple(
            RoleView(
                role=r["role"],
                scope_type=r["scope_type"],
                scope_id=r["scope_id"],
                scope_name=r["scope_name"],
            )
            for r in role_rows
        )

        return AccountProfile(
            account_id=account_row["account_id"],
            document_type=account_row["document_type"],
            document_number=account_row["document_number"],
            first_names=account_row["first_names"],
            paternal_surname=account_row["paternal_surname"],
            maternal_surname=account_row["maternal_surname"],
            contact_email=account_row["contact_email"],
            must_change_password=account_row["must_change_password"],
            roles=roles,
        )
