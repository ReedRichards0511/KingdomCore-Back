from __future__ import annotations

import httpx
import pytest
from pydantic import SecretStr

from kingdom.contexts.identity.domain.errors import InvalidCredentials, InvalidToken
from kingdom.contexts.identity.domain.value_objects.national_id import (
    DocumentType,
    NationalId,
)
from kingdom.contexts.identity.infrastructure.supabase.identity_provider import (
    SupabaseIdentityProvider,
)
from kingdom.platform.settings import SupabaseSettings
from kingdom.shared.domain.errors import ExternalServiceError, TooManyRequestsError


def _make_settings() -> SupabaseSettings:
    return SupabaseSettings(
        url="https://test.supabase.co",
        project_ref="test",
        publishable_key=SecretStr("pk"),
        service_role_key=SecretStr("sk"),
    )


async def test_un_401_de_supabase_en_el_login_se_traduce_a_error_del_proveedor() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "unauthorized"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = SupabaseIdentityProvider(settings=_make_settings(), client=client)
    nid = NationalId(DocumentType.CEDULA, "1804470738")

    with pytest.raises(ExternalServiceError) as exc_info:
        await provider.sign_in(nid, "password")

    assert exc_info.value.context.get("status") == 401


async def test_un_400_de_supabase_en_el_login_son_credenciales_incorrectas() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "invalid_grant"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = SupabaseIdentityProvider(settings=_make_settings(), client=client)
    nid = NationalId(DocumentType.CEDULA, "1804470738")

    with pytest.raises(InvalidCredentials):
        await provider.sign_in(nid, "password")


async def test_un_429_de_supabase_se_traduce_a_demasiadas_peticiones() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": "over_request_rate_limit"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = SupabaseIdentityProvider(settings=_make_settings(), client=client)
    nid = NationalId(DocumentType.CEDULA, "1804470738")

    with pytest.raises(TooManyRequestsError):
        await provider.sign_in(nid, "password")


async def test_una_respuesta_sin_access_token_se_traduce_a_error_del_proveedor() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"user": {"id": "00000000-0000-0000-0000-000000000001"}})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = SupabaseIdentityProvider(settings=_make_settings(), client=client)
    nid = NationalId(DocumentType.CEDULA, "1804470738")

    with pytest.raises(ExternalServiceError):
        await provider.sign_in(nid, "password")


async def test_un_401_de_supabase_en_el_refresh_es_token_invalido() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "invalid_grant"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = SupabaseIdentityProvider(settings=_make_settings(), client=client)

    with pytest.raises(InvalidToken):
        await provider.refresh("refresh-token")


async def test_si_el_logout_no_conecta_no_se_propaga_el_error() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("No connection")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = SupabaseIdentityProvider(settings=_make_settings(), client=client)

    await provider.sign_out("access-token")


async def test_el_logout_global_envia_scope_global() -> None:
    captured_params: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_params["scope"] = request.url.params.get("scope", "")
        return httpx.Response(204)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = SupabaseIdentityProvider(settings=_make_settings(), client=client)

    await provider.sign_out("access-token", everywhere=True)

    assert captured_params.get("scope") == "global"
