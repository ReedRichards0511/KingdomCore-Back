"""Comprobaciones minimas de que el esqueleto esta bien armado."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from kingdom.shared.domain.errors import BusinessRuleViolation, DomainError, NotFoundError
from kingdom.shared.infrastructure.clock import FrozenClock, SystemClock
from kingdom.shared.infrastructure.id_generator import Uuid7Generator


def test_uuid7_es_ordenable_por_tiempo() -> None:
    generator = Uuid7Generator()
    first = generator.generate()
    second = generator.generate()

    assert isinstance(first, UUID)
    assert first.version == 7
    assert first < second


def test_el_reloj_del_sistema_siempre_trae_zona_horaria() -> None:
    assert SystemClock().now().tzinfo is not None


def test_el_reloj_congelado_rechaza_datetimes_sin_zona() -> None:
    try:
        FrozenClock(datetime(2026, 10, 4, 14, 0))  # noqa: DTZ001 - es lo que se prueba
    except ValueError:
        return
    raise AssertionError("FrozenClock debio rechazar un datetime naive")


def test_los_errores_de_dominio_comparten_raiz() -> None:
    assert issubclass(NotFoundError, DomainError)
    assert issubclass(BusinessRuleViolation, DomainError)
    assert NotFoundError("sin resultados").code == "not_found"


def test_el_contexto_del_error_se_conserva() -> None:
    error = BusinessRuleViolation("saldo pendiente", enrollment_id="abc", balance=15.0)
    assert error.context == {"enrollment_id": "abc", "balance": 15.0}
