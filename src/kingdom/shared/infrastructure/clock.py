from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

PARISH_TIMEZONE = ZoneInfo("America/Guayaquil")


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)

    def today(self) -> date:
        return datetime.now(PARISH_TIMEZONE).date()


class FrozenClock:
    def __init__(self, instant: datetime) -> None:
        if instant.tzinfo is None:
            raise ValueError("FrozenClock exige un datetime con zona horaria")
        self._instant = instant

    def now(self) -> datetime:
        return self._instant

    def today(self) -> date:
        return self._instant.astimezone(PARISH_TIMEZONE).date()

    def advance(self, **timedelta_kwargs: float) -> None:
        from datetime import timedelta

        self._instant += timedelta(**timedelta_kwargs)
