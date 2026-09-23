from __future__ import annotations

from types import TracebackType
from typing import TYPE_CHECKING, Any, Self
from uuid import UUID

from kingdom.contexts.identity.domain.errors import InvalidCredentials, InvalidToken
from kingdom.contexts.identity.domain.value_objects.auth_session import AuthSession
from kingdom.shared.domain.errors import DomainError

if TYPE_CHECKING:
    from kingdom.contexts.identity.application.projections.account_profile import (
        AccountProfile,
    )
    from kingdom.contexts.identity.domain.entities.user_account import UserAccount
    from kingdom.contexts.identity.domain.value_objects.national_id import NationalId
    from kingdom.contexts.identity.domain.value_objects.password import NewPassword
    from kingdom.contexts.identity.domain.value_objects.token_claims import TokenClaims
    from kingdom.shared.domain.ports.unit_of_work import Connection


class FakeConnection:
    async def execute(self, query: str, *args: Any) -> str:
        return ""

    async def fetch(self, query: str, *args: Any) -> list[Any]:
        return []

    async def fetchrow(self, query: str, *args: Any) -> Any | None:
        return None

    async def fetchval(self, query: str, *args: Any) -> Any:
        return None

    async def executemany(self, query: str, args: Any) -> None:
        pass


class FakeUnitOfWork:
    def __init__(self, connection: Connection | None = None) -> None:
        self.committed = False
        self.rolled_back = False
        self.connection: Connection = connection or FakeConnection()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            self.rolled_back = True
        else:
            self.committed = True

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class FakeIdentityProvider:
    def __init__(
        self,
        credentials: dict[str, str] | None = None,
        users_by_number: dict[str, UUID] | None = None,
        change_password_error: DomainError | None = None,
    ) -> None:
        self.credentials: dict[str, str] = credentials or {}
        self.users_by_number: dict[str, UUID] = users_by_number or {}
        self.change_password_error: DomainError | None = change_password_error
        self.changed_passwords: list[tuple[UUID, str]] = []
        self.signed_out_tokens: list[tuple[str, bool]] = []

    async def sign_in(self, national_id: NationalId, password: str) -> AuthSession:
        expected = self.credentials.get(national_id.number)
        if expected is None or expected != password:
            raise InvalidCredentials()

        user_id = self.users_by_number.get(national_id.number, UUID(int=1))
        return AuthSession(
            access_token=f"fake-access-token-{national_id.number}",
            refresh_token=f"fake-refresh-token-{national_id.number}",
            expires_in=3600,
            external_user_id=user_id,
        )

    async def refresh(self, refresh_token: str) -> AuthSession:
        if not refresh_token or "invalid" in refresh_token:
            raise InvalidToken()

        number = refresh_token.replace("fake-refresh-token-", "")
        user_id = self.users_by_number.get(number, UUID(int=1))
        return AuthSession(
            access_token=f"fake-access-token-{number}-refreshed",
            refresh_token=f"fake-refresh-token-{number}-refreshed",
            expires_in=3600,
            external_user_id=user_id,
        )

    async def change_password(self, external_user_id: UUID, new_password: NewPassword) -> None:
        if self.change_password_error is not None:
            raise self.change_password_error
        self.changed_passwords.append((external_user_id, new_password.value))
        for num, uid in self.users_by_number.items():
            if uid == external_user_id:
                self.credentials[num] = new_password.value

    async def sign_out(self, access_token: str, *, everywhere: bool = False) -> None:
        self.signed_out_tokens.append((access_token, everywhere))


class FakeUserAccountRepository:
    def __init__(self, accounts: list[UserAccount] | None = None) -> None:
        self.accounts_by_external_id: dict[UUID, UserAccount] = {
            acc.external_user_id: acc for acc in (accounts or [])
        }
        self.logins: list[UUID] = []
        self.password_changes: list[UUID] = []

    async def get_by_external_id(self, external_user_id: UUID) -> UserAccount | None:
        return self.accounts_by_external_id.get(external_user_id)

    async def record_login(self, account: UserAccount) -> None:
        self.accounts_by_external_id[account.external_user_id] = account
        self.logins.append(account.id)

    async def save_password_change(self, account: UserAccount) -> None:
        self.accounts_by_external_id[account.external_user_id] = account
        self.password_changes.append(account.id)


class FakeTokenVerifier:
    def __init__(self, claims_by_token: dict[str, TokenClaims] | None = None) -> None:
        self.claims_by_token: dict[str, TokenClaims] = claims_by_token or {}

    async def verify(self, token: str) -> TokenClaims:
        if token not in self.claims_by_token:
            raise InvalidToken()
        return self.claims_by_token[token]


class FakeAccountProfileQuery:
    def __init__(self, profiles: dict[UUID, AccountProfile] | None = None) -> None:
        self.profiles = profiles or {}

    async def profile_of(self, account_id: UUID) -> AccountProfile | None:
        return self.profiles.get(account_id)
