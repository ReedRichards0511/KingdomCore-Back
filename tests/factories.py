from __future__ import annotations

from typing import Any
from uuid import UUID

from kingdom.contexts.identity.domain.entities.user_account import UserAccount
from kingdom.contexts.identity.domain.value_objects.national_id import (
    DocumentType,
    NationalId,
)
from kingdom.contexts.identity.domain.value_objects.role_assignment import (
    RoleAssignment,
    RoleName,
    ScopeType,
)

DEFAULT_ACCOUNT_ID = UUID("0191e4f2-7000-7000-8000-000000000001")
DEFAULT_PERSON_ID = UUID("0191e4f2-7000-7000-8000-000000000002")
DEFAULT_EXTERNAL_USER_ID = UUID("ba292b66-683b-4ebb-a0ca-e10729586d27")
DEFAULT_PARISH_ID = UUID("0191e4f2-7000-7000-8000-000000000003")


def make_user_account(**overrides: Any) -> UserAccount:
    default_role = RoleAssignment(
        role=RoleName.PARISH_ADMIN,
        scope_type=ScopeType.PARISH,
        scope_id=DEFAULT_PARISH_ID,
    )

    data: dict[str, Any] = {
        "id": DEFAULT_ACCOUNT_ID,
        "person_id": DEFAULT_PERSON_ID,
        "external_user_id": DEFAULT_EXTERNAL_USER_ID,
        "national_id": NationalId(DocumentType.CEDULA, "1804470738"),
        "is_active": True,
        "must_change_password": True,
        "last_login_at": None,
        "roles": (default_role,),
        "updated_at": None,
    }
    data.update(overrides)
    return UserAccount(**data)
