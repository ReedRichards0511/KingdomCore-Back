from __future__ import annotations

from typing import Protocol


class SignInThrottle(Protocol):
    def ensure_allowed(self, key: str) -> None: ...

    def record_failure(self, key: str) -> None: ...

    def reset(self, key: str) -> None: ...
