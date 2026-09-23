from __future__ import annotations

import math
from collections import deque
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from kingdom.contexts.identity.domain.errors import TooManySignInAttempts

if TYPE_CHECKING:
    from kingdom.shared.domain.ports.clock import Clock


class InMemorySignInThrottle:
    def __init__(
        self,
        *,
        clock: Clock,
        max_failures: int = 5,
        window_seconds: int = 900,
        max_tracked_keys: int = 10_000,
    ) -> None:
        self._clock = clock
        self._max_failures = max_failures
        self._window_seconds = window_seconds
        self._max_tracked_keys = max_tracked_keys
        self._failures: dict[str, deque[datetime]] = {}

    def tracked_keys(self) -> frozenset[str]:
        return frozenset(self._failures.keys())

    def _prune(self, key: str, now: datetime) -> deque[datetime] | None:
        queue = self._failures.get(key)
        if not queue:
            return None

        window = timedelta(seconds=self._window_seconds)
        while queue and (now - queue[0]) >= window:
            queue.popleft()

        if not queue:
            self._failures.pop(key, None)
            return None

        return queue

    def _sweep(self, now: datetime) -> None:
        for key in list(self._failures.keys()):
            self._prune(key, now)

        if len(self._failures) >= self._max_tracked_keys:
            sorted_keys = sorted(
                self._failures.keys(),
                key=lambda k: self._failures[k][-1],
            )
            to_remove = len(self._failures) - self._max_tracked_keys + 1
            for k in sorted_keys[:to_remove]:
                self._failures.pop(k, None)

    def ensure_allowed(self, key: str) -> None:
        now = self._clock.now()
        queue = self._prune(key, now)
        if not queue:
            return

        if len(queue) >= self._max_failures:
            oldest = queue[0]
            window = timedelta(seconds=self._window_seconds)
            retry_after = max(1, math.ceil((oldest + window - now).total_seconds()))
            raise TooManySignInAttempts(retry_after_seconds=retry_after)

    def record_failure(self, key: str) -> None:
        now = self._clock.now()
        if key not in self._failures and len(self._failures) >= self._max_tracked_keys:
            self._sweep(now)
        self._failures.setdefault(key, deque()).append(now)

    def reset(self, key: str) -> None:
        self._failures.pop(key, None)
