from __future__ import annotations

from uuid import UUID

from pydantic import SecretStr

from kingdom.contexts.identity.domain.value_objects.national_id import DocumentType
from kingdom.shared.api.schemas import ApiModel, ApiRequest


class SignInRequest(ApiRequest):
    document_type: DocumentType = DocumentType.CEDULA
    document_number: str
    password: SecretStr


class RefreshRequest(ApiRequest):
    refresh_token: str


class ChangePasswordRequest(ApiRequest):
    current_password: SecretStr
    new_password: SecretStr


class SessionResponse(ApiModel):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "bearer"
    must_change_password: bool


class RoleResponse(ApiModel):
    role: str
    scope_type: str
    scope_id: UUID
    scope_name: str | None


class ProfileResponse(ApiModel):
    account_id: UUID
    document_type: str
    document_number: str
    first_names: str
    paternal_surname: str
    maternal_surname: str | None
    contact_email: str | None
    must_change_password: bool
    roles: list[RoleResponse]
