from __future__ import annotations

from typing import TYPE_CHECKING, Protocol
from uuid import UUID

if TYPE_CHECKING:
    from kingdom.contexts.identity.application.projections.account_profile import (
        AccountProfile,
    )


class AccountProfileQuery(Protocol):
    async def profile_of(self, account_id: UUID) -> AccountProfile | None: ...
