from __future__ import annotations

from types import TracebackType
from typing import Any, Protocol, Self


class Connection(Protocol):
    async def execute(self, query: str, *args: Any) -> str: ...

    async def fetch(self, query: str, *args: Any) -> list[Any]: ...

    async def fetchrow(self, query: str, *args: Any) -> Any | None: ...

    async def fetchval(self, query: str, *args: Any) -> Any: ...

    async def executemany(self, query: str, args: Any) -> None: ...


class UnitOfWork(Protocol):
    @property
    def connection(self) -> Connection: ...

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
