"""Puerto de unidad de trabajo.

Un caso de uso que escribe en varias tablas abre una unidad de trabajo y todo
queda dentro de la misma transaccion. Inscribir a un alumno toca
``enrollments``, ``charges`` y ``audit_log``: o entran las tres o no entra
ninguna.
"""

from __future__ import annotations

from types import TracebackType
from typing import Any, Protocol, Self


class Connection(Protocol):
    """Lo minimo que un repositorio necesita de una conexion."""

    async def execute(self, query: str, *args: Any) -> str: ...

    async def fetch(self, query: str, *args: Any) -> list[Any]: ...

    async def fetchrow(self, query: str, *args: Any) -> Any | None: ...

    async def fetchval(self, query: str, *args: Any) -> Any: ...

    async def executemany(self, query: str, args: Any) -> None: ...


class UnitOfWork(Protocol):
    """Transaccion con alcance de caso de uso."""

    connection: Connection

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
