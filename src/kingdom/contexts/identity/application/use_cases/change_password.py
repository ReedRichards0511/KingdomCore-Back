from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from kingdom.contexts.identity.domain.errors import (
    AccountNotProvisioned,
    InvalidCredentials,
    InvalidCurrentPassword,
    PasswordReused,
)

if TYPE_CHECKING:
    from kingdom.contexts.identity.application.ports.sign_in_throttle import SignInThrottle
    from kingdom.contexts.identity.domain.ports.identity_provider import IdentityProvider
    from kingdom.contexts.identity.domain.ports.user_account_repository import (
        UserAccountRepository,
    )
    from kingdom.contexts.identity.domain.value_objects.auth_session import AuthSession
    from kingdom.contexts.identity.domain.value_objects.national_id import NationalId
    from kingdom.contexts.identity.domain.value_objects.password import NewPassword
    from kingdom.shared.domain.ports.clock import Clock
    from kingdom.shared.domain.ports.unit_of_work import UnitOfWork


def _throttle_key(national_id: NationalId) -> str:
    return f"{national_id.document_type.value}:{national_id.number}"


@dataclass(frozen=True, slots=True)
class ChangePasswordCommand:
    account_external_id: UUID
    current_password: str
    new_password: NewPassword


class ChangePassword:
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

    async def execute(self, command: ChangePasswordCommand) -> AuthSession:
        async with self._unit_of_work:
            account = await self._accounts.get_by_external_id(command.account_external_id)
            if account is None:
                raise AccountNotProvisioned()
            account.ensure_can_sign_in()

        if command.new_password.value == command.current_password:
            raise PasswordReused()

        key = _throttle_key(account.national_id)
        self._throttle.ensure_allowed(key)

        try:
            verification = await self._identity_provider.sign_in(
                account.national_id, command.current_password
            )
        except InvalidCredentials as exc:
            self._throttle.record_failure(key)
            raise InvalidCurrentPassword() from exc

        self._throttle.reset(key)

        try:
            await self._identity_provider.change_password(
                account.external_user_id, command.new_password
            )
        except Exception:
            await self._identity_provider.sign_out(verification.access_token)
            raise

        await self._identity_provider.sign_out(verification.access_token, everywhere=True)

        async with self._unit_of_work:
            account.complete_password_change(at=self._clock.now())
            await self._accounts.save_password_change(account)

        return await self._identity_provider.sign_in(
            account.national_id, command.new_password.value
        )
