from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AuthSession:
    access_token: str
    refresh_token: str
    expires_in: int
    external_user_id: UUID

    def __repr__(self) -> str:
        return (
            f"AuthSession(external_user_id={self.external_user_id}, expires_in={self.expires_in})"
        )
