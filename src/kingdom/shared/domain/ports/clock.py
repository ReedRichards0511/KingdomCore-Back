"""Puerto del reloj.

El dominio nunca llama a ``datetime.now()`` de forma directa. Pide la hora a
este puerto, y asi las reglas que dependen del tiempo (ventana de
justificacion de faltas, cierre de anio lectivo, vigencia del tarifario) se
pueden probar sin trucos.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        """Instante actual, siempre con zona horaria."""
        ...

    def today(self) -> date:
        """Fecha actual en la zona horaria de la parroquia."""
        ...
