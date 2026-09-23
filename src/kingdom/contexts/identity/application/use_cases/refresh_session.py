from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from kingdom.contexts.identity.application.use_cases.sign_in import SignInResult
from kingdom.contexts.identity.domain.errors import AccountNotProvisioned

if TYPE_CHECKING:
    from kingdom.contexts.identity.domain.ports.identity_provider import IdentityProvider
    from kingdom.contexts.identity.domain.ports.user_account_repository import (
        UserAccountRepository,
    )
    from kingdom.shared.domain.ports.unit_of_work import UnitOfWork


@dataclass(frozen=True, slots=True)
class RefreshSessionCommand:
    refresh_token: str


class RefreshSession:
    def __init__(
        self,
        *,
        identity_provider: IdentityProvider,
        accounts: UserAccountRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._identity_provider = identity_provider
        self._accounts = accounts
        self._unit_of_work = unit_of_work

    async def execute(self, command: RefreshSessionCommand) -> SignInResult:
        session = await self._identity_provider.refresh(command.refresh_token)
        async with self._unit_of_work:
            account = await self._accounts.get_by_external_id(session.external_user_id)
            if account is None:
                raise AccountNotProvisioned()
            account.ensure_can_sign_in()

        return SignInResult(
            session=session,
            must_change_password=account.must_change_password,
        )
