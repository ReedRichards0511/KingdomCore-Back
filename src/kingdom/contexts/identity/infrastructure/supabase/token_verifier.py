from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from uuid import UUID

import jwt
from jwt import (
    PyJWKClient,
    PyJWKClientConnectionError,
    PyJWKClientError,
    PyJWTError,
)

from kingdom.contexts.identity.domain.errors import InvalidToken
from kingdom.contexts.identity.domain.value_objects.token_claims import TokenClaims
from kingdom.shared.domain.errors import ExternalServiceError

if TYPE_CHECKING:
    from kingdom.platform.settings import SupabaseSettings


class SupabaseTokenVerifier:
    def __init__(
        self,
        *,
        settings: SupabaseSettings,
        jwks_client: PyJWKClient | None = None,
    ) -> None:
        self._settings = settings
        self._jwks_client = jwks_client or PyJWKClient(
            self._settings.jwks_url,
            cache_keys=True,
            lifespan=self._settings.jwks_cache_seconds,
        )

    async def verify(self, token: str) -> TokenClaims:
        try:
            signing_key = await asyncio.to_thread(self._jwks_client.get_signing_key_from_jwt, token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256"],
                audience=self._settings.jwt_audience,
                issuer=self._settings.issuer,
                options={"require": ["exp", "sub", "aud", "iss"]},
            )
            sub = payload["sub"]
            return TokenClaims(external_user_id=UUID(sub))
        except PyJWKClientConnectionError as exc:
            raise ExternalServiceError(
                "No se pudo obtener las llaves del proveedor de identidad"
            ) from exc
        except (PyJWTError, PyJWKClientError, KeyError, ValueError) as exc:
            raise InvalidToken() from exc
