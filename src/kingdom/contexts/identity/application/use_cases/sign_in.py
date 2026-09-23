from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from kingdom.contexts.identity.domain.errors import (
    AccountNotProvisioned,
    InvalidCredentials,
)

if TYPE_CHECKING:
    from kingdom.contexts.identity.application.ports.sign_in_throttle import SignInThrottle
    from kingdom.contexts.identity.domain.ports.identity_provider import IdentityProvider
    from kingdom.contexts.identity.domain.ports.user_account_repository import (
        UserAccountRepository,
    )
    from kingdom.contexts.identity.domain.value_objects.auth_session import AuthSession
    from kingdom.contexts.identity.domain.value_objects.national_id import NationalId
    from kingdom.shared.domain.ports.clock import Clock
    from kingdom.shared.domain.ports.unit_of_work import UnitOfWork


def _throttle_key(national_id: NationalId) -> str:
    return f"{national_id.document_type.value}:{national_id.number}"


@dataclass(frozen=True, slots=True)
class SignInCommand:
    national_id: NationalId
    password: str


@dataclass(frozen=True, slots=True)
class SignInResult:
    session: AuthSession
    must_change_password: bool


class SignIn:
    def __init__(
        self,
        *,
        identity_provider: IdentityProvider,
        accounts: UserAccountRepository,
        clock: Clock,
        unit_of_work: UnitOfWork,
        throttle: SignInThrottle,
    ) -> None:
        self._identity_provider = identity_provider
        self._accounts = accounts
        self._clock = clock
        self._unit_of_work = unit_of_work
        self._throttle = throttle

    async def execute(self, command: SignInCommand) -> SignInResult:
        key = _throttle_key(command.national_id)
        self._throttle.ensure_allowed(key)
        try:
            session = await self._identity_provider.sign_in(command.national_id, command.password)
        except InvalidCredentials:
            self._throttle.record_failure(key)
            raise

        try:
            async with self._unit_of_work:
                account = await self._accounts.get_by_external_id(session.external_user_id)
                if account is None:
                    raise AccountNotProvisioned()
                account.ensure_can_sign_in()
                account.record_login(at=self._clock.now())
                await self._accounts.record_login(account)
        except Exception:
            await self._identity_provider.sign_out(session.access_token)
            raise

        self._throttle.reset(key)

        return SignInResult(
            session=session,
            must_change_password=account.must_change_password,
        )
