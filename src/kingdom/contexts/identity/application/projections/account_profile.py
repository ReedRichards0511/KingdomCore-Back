from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RoleView:
    role: str
    scope_type: str
    scope_id: UUID
    scope_name: str | None


@dataclass(frozen=True, slots=True)
class AccountProfile:
    account_id: UUID
    document_type: str
    document_number: str
    first_names: str
    paternal_surname: str
    maternal_surname: str | None
    contact_email: str | None
    must_change_password: bool
    roles: tuple[RoleView, ...]
