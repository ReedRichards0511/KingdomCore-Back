"""Puerto del generador de identificadores.

Todos los identificadores del sistema son UUIDv7 y nacen en Python. La base de
datos no genera ninguno: no hay ``gen_random_uuid()`` ni secuencias en el
esquema.
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID


class IdGenerator(Protocol):
    def generate(self) -> UUID:
        """Devuelve un UUIDv7 nuevo, ordenable por tiempo de creacion."""
        ...
