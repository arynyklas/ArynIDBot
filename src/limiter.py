"""Request budgets per key: GCRA, the generic cell rate algorithm."""

from collections.abc import Callable
from dataclasses import dataclass
import time

from src import constants


@dataclass(frozen=True, slots=True)
class Verdict:
    allowed: bool
    warn: bool = False
    """The first refusal since the key was last allowed: worth one notice."""
    retry_after: float = 0.0
    """Seconds until the key is allowed again; 0 when it is allowed now."""


_ALLOWED = Verdict(allowed=True)


class RateLimiter:
    """`burst` requests back to back per key, then one more every `interval` seconds.

    Each key keeps one number: the time its budget will be full again. A key
    past that time is the same as a new one, so a sweep forgets it and memory
    follows the keys active within the last `burst * interval` seconds. Refused
    requests cost nothing: a key flooding while over budget recovers on time.
    """

    def __init__(
        self,
        burst: int,
        interval: float,
        *,
        clock: Callable[[], float] = time.monotonic,
        sweep_interval: float = constants.LIMITER_SWEEP_INTERVAL,
    ) -> None:
        self._interval = interval
        # How far ahead of now a key's full-budget time may run while it still
        # gets a request through.
        self._tolerance = interval * (burst - 1)
        self._clock = clock
        self._sweep_interval = sweep_interval
        self._next_sweep = clock() + sweep_interval
        self._full_at: dict[int, float] = {}
        self._warned: set[int] = set()

    def hit(self, key: int) -> Verdict:
        now = self._clock()

        if now >= self._next_sweep:
            self._sweep(now)

        full_at = max(self._full_at.get(key, now), now)

        if full_at - now > self._tolerance:
            warn = key not in self._warned
            self._warned.add(key)

            return Verdict(
                allowed=False, warn=warn, retry_after=full_at - self._tolerance - now
            )

        self._full_at[key] = full_at + self._interval
        self._warned.discard(key)

        return _ALLOWED

    def _sweep(self, now: float) -> None:
        idle = [key for key, full_at in self._full_at.items() if full_at <= now]

        for key in idle:
            del self._full_at[key]
            self._warned.discard(key)

        self._next_sweep = now + self._sweep_interval
