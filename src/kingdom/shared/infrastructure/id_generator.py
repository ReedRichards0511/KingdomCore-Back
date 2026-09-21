"""Generacion de UUIDv7.

Python 3.13 no trae ``uuid7`` en la libreria estandar, asi que usamos
``uuid_utils``. La version 7 lleva marca de tiempo en los bits altos: los
identificadores quedan ordenados por creacion y los indices B-tree de Postgres
no sufren la fragmentacion que causa la version 4.
"""

from __future__ import annotations

from uuid import UUID

import uuid_utils


class Uuid7Generator:
    def generate(self) -> UUID:
        return UUID(str(uuid_utils.uuid7()))


class SequentialIdGenerator:
    """Generador determinista para pruebas."""

    def __init__(self, prefix: str = "00000000-0000-7000-8000") -> None:
        self._prefix = prefix
        self._counter = 0

    def generate(self) -> UUID:
        self._counter += 1
        return UUID(f"{self._prefix}-{self._counter:012d}")

