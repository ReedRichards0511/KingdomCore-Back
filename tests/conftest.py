"""Fixtures compartidas por toda la suite."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from kingdom.shared.infrastructure.clock import FrozenClock
from kingdom.shared.infrastructure.id_generator import SequentialIdGenerator


@pytest.fixture
def clock() -> FrozenClock:
    """Reloj detenido en un domingo de catequesis del ciclo 2026-2027."""
    return FrozenClock(datetime(2026, 10, 4, 14, 0, tzinfo=UTC))


@pytest.fixture
def ids() -> SequentialIdGenerator:
    return SequentialIdGenerator()
