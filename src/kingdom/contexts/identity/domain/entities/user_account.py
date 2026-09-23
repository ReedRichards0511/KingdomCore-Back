from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from kingdom.contexts.identity.domain.errors import (
    AccountDisabled,
    PasswordChangeRequired,
)
from kingdom.contexts.identity.domain.value_objects.role_assignment import (
    RoleAssignment,
    RoleName,
    ScopeType,
)
from kingdom.shared.domain.errors import PermissionDeniedError

if TYPE_CHECKING:
    from kingdom.contexts.identity.domain.value_objects.national_id import NationalId


@dataclass(slots=True)
class UserAccount:
    id: UUID
    person_id: UUID
    external_user_id: UUID
    national_id: NationalId
    is_active: bool
    must_change_password: bool
    last_login_at: datetime | None = None
    roles: tuple[RoleAssignment, ...] = ()
    updated_at: datetime | None = None

    def ensure_can_sign_in(self) -> None:
        if not self.is_active:
            raise AccountDisabled()

    def ensure_password_is_current(self) -> None:
        if self.must_change_password:
            raise PasswordChangeRequired()

    def ensure_has_any_role(self, required: frozenset[RoleName]) -> None:
        current_roles = {r.role for r in self.roles}
        if not current_roles.intersection(required):
            raise PermissionDeniedError(
                "No tiene los permisos requeridos",
                required=[r.value for r in required],
            )

    def has_role_in_scope(self, role: RoleName, scope_type: ScopeType, scope_id: UUID) -> bool:
        return any(
            r.role == role and r.scope_type == scope_type and r.scope_id == scope_id
            for r in self.roles
        )

    def record_login(self, *, at: datetime) -> None:
        self.last_login_at = at

    def complete_password_change(self, *, at: datetime) -> None:
        self.must_change_password = False
        self.updated_at = at
