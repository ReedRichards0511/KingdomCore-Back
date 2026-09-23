from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from kingdom.contexts.identity.domain.entities.user_account import UserAccount
from kingdom.contexts.identity.domain.value_objects.national_id import (
    DocumentType,
    NationalId,
)
from kingdom.contexts.identity.domain.value_objects.role_assignment import (
    RoleAssignment,
    RoleName,
    ScopeType,
)

if TYPE_CHECKING:
    import asyncpg

    from kingdom.shared.domain.ports.unit_of_work import UnitOfWork


class PostgresUserAccountRepository:
    def __init__(self, *, unit_of_work: UnitOfWork) -> None:
        self._uow = unit_of_work

    async def get_by_external_id(self, external_user_id: UUID) -> UserAccount | None:
        row: asyncpg.Record | None = await self._uow.connection.fetchrow(
            """
            SELECT ua.id, ua.person_id, ua.external_user_id, ua.is_active,
                   ua.must_change_password, ua.last_login_at, ua.updated_at,
                   p.document_type, p.document_number
              FROM user_accounts ua
              JOIN persons p ON p.id = ua.person_id
             WHERE ua.external_user_id = $1
               AND ua.deleted_at IS NULL
               AND p.deleted_at IS NULL
            """,
            external_user_id,
        )
        if row is None:
            return None

        role_rows: list[asyncpg.Record] = await self._uow.connection.fetch(
            """
            SELECT role, scope_type, scope_id
              FROM role_assignments
             WHERE user_account_id = $1
               AND revoked_at IS NULL
               AND deleted_at IS NULL
            """,
            row["id"],
        )

        roles = tuple(
            RoleAssignment(
                role=RoleName(r["role"]),
                scope_type=ScopeType(r["scope_type"]),
                scope_id=r["scope_id"],
            )
            for r in role_rows
        )

        return UserAccount(
            id=row["id"],
            person_id=row["person_id"],
            external_user_id=row["external_user_id"],
            national_id=NationalId(
                document_type=DocumentType(row["document_type"]),
                number=row["document_number"],
            ),
            is_active=row["is_active"],
            must_change_password=row["must_change_password"],
            last_login_at=row["last_login_at"],
            roles=roles,
            updated_at=row["updated_at"],
        )

    async def record_login(self, account: UserAccount) -> None:
        await self._uow.connection.execute(
            """
            UPDATE user_accounts
               SET last_login_at = $2
             WHERE id = $1
            """,
            account.id,
            account.last_login_at,
        )

    async def save_password_change(self, account: UserAccount) -> None:
        await self._uow.connection.execute(
            """
            UPDATE user_accounts
               SET must_change_password = $2,
                   updated_at = $3,
                   updated_by = $4
             WHERE id = $1
            """,
            account.id,
            account.must_change_password,
            account.updated_at,
            account.id,
        )
