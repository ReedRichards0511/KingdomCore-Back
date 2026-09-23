from __future__ import annotations

import pytest

from kingdom.contexts.identity.domain.errors import TooManySignInAttempts
from kingdom.contexts.identity.infrastructure.throttling.in_memory_sign_in_throttle import (
    InMemorySignInThrottle,
)
from kingdom.shared.infrastructure.clock import FrozenClock


def test_tras_cinco_fallos_se_bloquea_el_documento(clock: FrozenClock) -> None:
    throttle = InMemorySignInThrottle(clock=clock, max_failures=5, window_seconds=900)
    key = "cedula:1804470738"

    for _ in range(5):
        throttle.ensure_allowed(key)
        throttle.record_failure(key)

    with pytest.raises(TooManySignInAttempts) as exc_info:
        throttle.ensure_allowed(key)

    assert exc_info.value.context.get("retry_after_seconds") == 900


def test_el_bloqueo_se_levanta_al_pasar_la_ventana(clock: FrozenClock) -> None:
    throttle = InMemorySignInThrottle(clock=clock, max_failures=5, window_seconds=900)
    key = "cedula:1804470738"

    for _ in range(5):
        throttle.record_failure(key)

    with pytest.raises(TooManySignInAttempts):
        throttle.ensure_allowed(key)

    clock.advance(seconds=901)
    throttle.ensure_allowed(key)


def test_un_login_correcto_limpia_los_fallos(clock: FrozenClock) -> None:
    throttle = InMemorySignInThrottle(clock=clock, max_failures=5, window_seconds=900)
    key = "cedula:1804470738"

    for _ in range(4):
        throttle.record_failure(key)

    throttle.reset(key)

    for _ in range(4):
        throttle.record_failure(key)

    throttle.ensure_allowed(key)


def test_el_bloqueo_de_un_documento_no_afecta_a_otro(clock: FrozenClock) -> None:
    throttle = InMemorySignInThrottle(clock=clock, max_failures=5, window_seconds=900)
    blocked_key = "cedula:1804470738"
    other_key = "cedula:1712345678"

    for _ in range(5):
        throttle.record_failure(blocked_key)

    with pytest.raises(TooManySignInAttempts):
        throttle.ensure_allowed(blocked_key)

    throttle.ensure_allowed(other_key)


def test_los_fallos_vencidos_se_descartan_al_llegar_al_tope(clock: FrozenClock) -> None:
    throttle = InMemorySignInThrottle(
        clock=clock,
        max_failures=5,
        window_seconds=900,
        max_tracked_keys=2,
    )
    throttle.record_failure("cedula:1111111111")
    throttle.record_failure("cedula:2222222222")

    clock.advance(seconds=901)
    throttle.record_failure("cedula:3333333333")

    assert throttle.tracked_keys() == frozenset({"cedula:3333333333"})


def test_al_llegar_al_tope_se_descarta_la_clave_mas_antigua(clock: FrozenClock) -> None:
    throttle = InMemorySignInThrottle(
        clock=clock,
        max_failures=5,
        window_seconds=900,
        max_tracked_keys=2,
    )
    throttle.record_failure("cedula:1111111111")
    clock.advance(seconds=1)
    throttle.record_failure("cedula:2222222222")
    clock.advance(seconds=1)
    throttle.record_failure("cedula:3333333333")

    assert throttle.tracked_keys() == frozenset({"cedula:2222222222", "cedula:3333333333"})
