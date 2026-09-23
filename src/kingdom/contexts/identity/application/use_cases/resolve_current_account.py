from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from kingdom.contexts.identity.domain.errors import AccountNotProvisioned

if TYPE_CHECKING:
    from kingdom.contexts.identity.domain.entities.user_account import UserAccount
    from kingdom.contexts.identity.domain.ports.token_verifier import TokenVerifier
    from kingdom.contexts.identity.domain.ports.user_account_repository import (
        UserAccountRepository,
    )
    from kingdom.shared.domain.ports.unit_of_work import UnitOfWork


@dataclass(frozen=True, slots=True)
class ResolveCurrentAccountQuery:
    access_token: str


class ResolveCurrentAccount:
    def __init__(
        self,
        *,
        token_verifier: TokenVerifier,
        accounts: UserAccountRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._token_verifier = token_verifier
        self._accounts = accounts
        self._unit_of_work = unit_of_work

    async def execute(self, query: ResolveCurrentAccountQuery) -> UserAccount:
        claims = await self._token_verifier.verify(query.access_token)
        async with self._unit_of_work:
            account = await self._accounts.get_by_external_id(claims.external_user_id)
            if account is None:
                raise AccountNotProvisioned()
            account.ensure_can_sign_in()

        return account
