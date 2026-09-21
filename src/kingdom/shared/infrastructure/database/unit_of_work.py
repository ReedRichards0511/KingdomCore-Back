"""Unidad de trabajo sobre una transaccion de asyncpg."""

from __future__ import annotations

from types import TracebackType
from typing import TYPE_CHECKING, Any, Self

if TYPE_CHECKING:
    import asyncpg


class PostgresUnitOfWork:
    """Toma una conexion del pool y la envuelve en una transaccion.

    Al salir del ``async with`` sin excepcion hace commit. Si hubo excepcion,
    hace rollback y la deja propagar: un caso de uso que falla a la mitad no
    deja cargos huerfanos.
    """

    def __init__(self, pool: asyncpg.Pool[Any]) -> None:
        self._pool = pool
        self._connection: asyncpg.Connection[Any] | None = None
        self._transaction: Any | None = None
        self._finished = False

    @property
    def connection(self) -> asyncpg.Connection[Any]:
        if self._connection is None:
            raise RuntimeError("La unidad de trabajo no esta abierta")
        return self._connection

    async def __aenter__(self) -> Self:
        self._connection = await self._pool.acquire()
        self._transaction = self.connection.transaction()
        await self._transaction.start()
        self._finished = False
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        try:
            if not self._finished:
                if exc_type is None:
                    await self.commit()
                else:
                    await self.rollback()
        finally:
            if self._connection is not None:
                await self._pool.release(self._connection)
                self._connection = None
                self._transaction = None

    async def commit(self) -> None:
        if self._transaction is None:
            raise RuntimeError("La unidad de trabajo no esta abierta")
        await self._transaction.commit()
        self._finished = True

    async def rollback(self) -> None:
        if self._transaction is None:
            raise RuntimeError("La unidad de trabajo no esta abierta")
        await self._transaction.rollback()
        self._finished = True
