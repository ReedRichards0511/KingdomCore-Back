from __future__ import annotations

from typing import TYPE_CHECKING, Protocol
from uuid import UUID

if TYPE_CHECKING:
    from kingdom.contexts.identity.domain.value_objects.auth_session import AuthSession
    from kingdom.contexts.identity.domain.value_objects.national_id import NationalId
    from kingdom.contexts.identity.domain.value_objects.password import NewPassword


class IdentityProvider(Protocol):
    async def sign_in(self, national_id: NationalId, password: str) -> AuthSession: ...

    async def refresh(self, refresh_token: str) -> AuthSession: ...

    async def change_password(self, external_user_id: UUID, new_password: NewPassword) -> None: ...

    async def sign_out(self, access_token: str, *, everywhere: bool = False) -> None: ...
