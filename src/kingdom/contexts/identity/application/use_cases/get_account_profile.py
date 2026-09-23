from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from kingdom.shared.domain.errors import NotFoundError

if TYPE_CHECKING:
    from kingdom.contexts.identity.application.ports.account_profile_query import (
        AccountProfileQuery,
    )
    from kingdom.contexts.identity.application.projections.account_profile import (
        AccountProfile,
    )
    from kingdom.shared.domain.ports.unit_of_work import UnitOfWork


@dataclass(frozen=True, slots=True)
class GetAccountProfileQuery:
    account_id: UUID


class GetAccountProfile:
    def __init__(
        self,
        *,
        profiles: AccountProfileQuery,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._profiles = profiles
        self._uow = unit_of_work

    async def execute(self, query: GetAccountProfileQuery) -> AccountProfile:
        async with self._uow:
            profile = await self._profiles.profile_of(query.account_id)
            if profile is None:
                raise NotFoundError(f"No se encontro el perfil de la cuenta {query.account_id}")
            return profile
