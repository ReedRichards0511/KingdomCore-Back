from __future__ import annotations

from typing import TYPE_CHECKING, Protocol
from uuid import UUID

if TYPE_CHECKING:
    from kingdom.contexts.identity.domain.entities.user_account import UserAccount


class UserAccountRepository(Protocol):
    async def get_by_external_id(self, external_user_id: UUID) -> UserAccount | None: ...

    async def record_login(self, account: UserAccount) -> None: ...

    async def save_password_change(self, account: UserAccount) -> None: ...
