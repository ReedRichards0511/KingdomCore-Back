from __future__ import annotations

from typing import Any

import pytest
from jwt import PyJWKClientConnectionError, PyJWKClientError
from pydantic import SecretStr

from kingdom.contexts.identity.domain.errors import InvalidToken
from kingdom.contexts.identity.infrastructure.supabase.token_verifier import (
    SupabaseTokenVerifier,
)
from kingdom.platform.settings import SupabaseSettings
from kingdom.shared.domain.errors import ExternalServiceError


def _make_settings() -> SupabaseSettings:
    return SupabaseSettings(
        url="https://test.supabase.co",
        project_ref="test",
        publishable_key=SecretStr("pk"),
        service_role_key=SecretStr("sk"),
    )


class FailingJwksClient:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    def get_signing_key_from_jwt(self, _token: str) -> Any:
        raise self._exc


async def test_si_no_hay_conexion_con_el_jwks_es_error_del_proveedor() -> None:
    jwks = FailingJwksClient(PyJWKClientConnectionError("Connection refused"))
    verifier = SupabaseTokenVerifier(
        settings=_make_settings(),
        jwks_client=jwks,  # type: ignore[arg-type]
    )

    with pytest.raises(ExternalServiceError):
        await verifier.verify("some.jwt.token")


async def test_un_token_mal_formado_es_token_invalido() -> None:
    jwks = FailingJwksClient(PyJWKClientError("Invalid key"))
    verifier = SupabaseTokenVerifier(
        settings=_make_settings(),
        jwks_client=jwks,  # type: ignore[arg-type]
    )

    with pytest.raises(InvalidToken):
        await verifier.verify("bad-token")
