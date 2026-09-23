from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class RoleName(StrEnum):
    ARCHDIOCESE_ADMIN = "archdiocese_admin"
    VICARIATE_ADMIN = "vicariate_admin"
    PARISH_ADMIN = "parish_admin"
    COMMUNITY_ADMIN = "community_admin"
    CATECHIST = "catechist"
    REPRESENTATIVE = "representative"
    CATECHUMEN = "catechumen"


class ScopeType(StrEnum):
    ARCHDIOCESE = "archdiocese"
    VICARIATE = "vicariate"
    PARISH = "parish"
    COMMUNITY = "community"


@dataclass(frozen=True, slots=True)
class RoleAssignment:
    role: RoleName
    scope_type: ScopeType
    scope_id: UUID
