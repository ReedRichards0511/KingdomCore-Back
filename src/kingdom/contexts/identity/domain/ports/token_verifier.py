from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from kingdom.contexts.identity.domain.value_objects.token_claims import TokenClaims


class TokenVerifier(Protocol):
    async def verify(self, token: str) -> TokenClaims: ...
