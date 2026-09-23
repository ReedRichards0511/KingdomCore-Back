from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from kingdom.contexts.identity.domain.errors import (
    InvalidCredentials,
    InvalidToken,
    WeakPassword,
)
from kingdom.contexts.identity.domain.value_objects.auth_session import AuthSession
from kingdom.shared.domain.errors import ExternalServiceError, TooManyRequestsError
from kingdom.shared.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from kingdom.contexts.identity.domain.value_objects.national_id import NationalId
    from kingdom.contexts.identity.domain.value_objects.password import NewPassword
    from kingdom.platform.settings import SupabaseSettings

logger = get_logger(__name__)


def _synthetic_email(national_id: NationalId, domain: str) -> str:
    return f"{national_id.number}@{domain}"


class SupabaseIdentityProvider:
    def __init__(self, *, settings: SupabaseSettings, client: httpx.AsyncClient) -> None:
        self._settings = settings
        self._client = client

    def _publishable_headers(self) -> dict[str, str]:
        key = self._settings.publishable_key.get_secret_value().strip()
        return {"apikey": key}

    def _admin_headers(self) -> dict[str, str]:
        key = self._settings.service_role_key.get_secret_value().strip()
        return {"apikey": key, "Authorization": f"Bearer {key}"}

    @retry(
        retry=retry_if_exception_type(httpx.TransportError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5),
        reraise=True,
    )
    async def _post_token(self, params: dict[str, str], payload: dict[str, str]) -> httpx.Response:
        return await self._client.post(
            self._settings.token_url,
            params=params,
            headers=self._publishable_headers(),
            json=payload,
        )

    @retry(
        retry=retry_if_exception_type(httpx.TransportError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5),
        reraise=True,
    )
    async def _put_admin_user(
        self, external_user_id: UUID, payload: dict[str, str]
    ) -> httpx.Response:
        return await self._client.put(
            f"{self._settings.admin_users_url}/{external_user_id}",
            headers=self._admin_headers(),
            json=payload,
        )

    async def sign_in(self, national_id: NationalId, password: str) -> AuthSession:
        email = _synthetic_email(national_id, self._settings.synthetic_email_domain)
        try:
            response = await self._post_token(
                params={"grant_type": "password"},
                payload={"email": email, "password": password},
            )
        except httpx.TransportError as exc:
            raise ExternalServiceError("No se pudo conectar con el proveedor de identidad") from exc

        if response.status_code == 429:
            raise TooManyRequestsError("Demasiados intentos, intente mas tarde")
        if response.status_code == 400:
            raise InvalidCredentials()
        if response.status_code >= 400:
            raise ExternalServiceError(
                "Error en el proveedor de identidad",
                status=response.status_code,
            )

        return _session_from(response)

    async def refresh(self, refresh_token: str) -> AuthSession:
        try:
            response = await self._post_token(
                params={"grant_type": "refresh_token"},
                payload={"refresh_token": refresh_token},
            )
        except httpx.TransportError as exc:
            raise ExternalServiceError("No se pudo conectar con el proveedor de identidad") from exc

        if response.status_code == 429:
            raise TooManyRequestsError("Demasiados intentos, intente mas tarde")
        if response.status_code in {400, 401, 403}:
            raise InvalidToken()
        if response.status_code >= 400:
            raise ExternalServiceError(
                "Error en el proveedor de identidad",
                status=response.status_code,
            )

        return _session_from(response)

    async def change_password(self, external_user_id: UUID, new_password: NewPassword) -> None:
        try:
            response = await self._put_admin_user(
                external_user_id,
                payload={"password": new_password.value},
            )
        except httpx.TransportError as exc:
            raise ExternalServiceError("No se pudo conectar con el proveedor de identidad") from exc

        if response.status_code == 422:
            raise WeakPassword()
        if response.status_code == 429:
            raise TooManyRequestsError("Demasiados intentos, intente mas tarde")
        if response.status_code >= 400:
            raise ExternalServiceError(
                "Error en el proveedor de identidad",
                status=response.status_code,
            )

    async def sign_out(self, access_token: str, *, everywhere: bool = False) -> None:
        scope = "global" if everywhere else "local"
        headers = {**self._publishable_headers(), "Authorization": f"Bearer {access_token}"}
        try:
            response = await self._client.post(
                self._settings.logout_url,
                params={"scope": scope},
                headers=headers,
            )
        except httpx.HTTPError as exc:
            logger.warning("supabase_sign_out_failed", scope=scope, error=type(exc).__name__)
            return
        if response.status_code >= 400:
            logger.warning("supabase_sign_out_rejected", scope=scope, status=response.status_code)


def _session_from(response: httpx.Response) -> AuthSession:
    try:
        data = response.json()
        return AuthSession(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_in=data["expires_in"],
            external_user_id=UUID(data["user"]["id"]),
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise ExternalServiceError("Respuesta inesperada del proveedor de identidad") from exc
