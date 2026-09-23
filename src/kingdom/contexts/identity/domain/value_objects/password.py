from __future__ import annotations

from dataclasses import dataclass

from kingdom.contexts.identity.domain.errors import WeakPassword


@dataclass(frozen=True, slots=True)
class NewPassword:
    value: str

    def __post_init__(self) -> None:
        if len(self.value) < 8:
            raise WeakPassword()

    def __repr__(self) -> str:
        return "NewPassword(***)"
