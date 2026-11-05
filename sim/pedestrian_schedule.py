"""Deterministic daily pedestrian cohorts for the accelerated demo clock."""

from dataclasses import dataclass
import random


MINUTE = 60
HOUR = 60 * MINUTE
DAY = 24 * HOUR
BACKGROUND_START = 6 * HOUR
BACKGROUND_END = 17 * HOUR


@dataclass(frozen=True)
class SpawnRequest:
    label: str
    return_times: tuple[float, ...]

    @property
    def count(self) -> int:
        return len(self.return_times)


class PedestrianSchedule:
    """Emit scheduled and background cohorts as clock thresholds are crossed."""

    def __init__(self, seed: int = 7):
        self.rng = random.Random(seed)
        self.previous_time: float | None = None
        self.fired: set[str] = set()
        self.next_background = self._next_background_after(BACKGROUND_START)

    def _next_background_after(self, time: float) -> float:
        return time + self.rng.uniform(20 * MINUTE, 40 * MINUTE)

    def _crossed(self, target: float, current: float) -> bool:
        if self.previous_time is None:
            return False
        if current >= self.previous_time:
            return self.previous_time < target <= current
        return target > self.previous_time or target <= current

    def _random_returns(
        self,
        start: float,
        count: int,
        minimum_minutes: int,
        maximum_minutes: int,
    ) -> tuple[float, ...]:
        return tuple(
            start + self.rng.uniform(minimum_minutes * MINUTE, maximum_minutes * MINUTE)
            for _ in range(count)
        )

    def _reset_day(self) -> None:
        self.fired.clear()
        self.next_background = self._next_background_after(BACKGROUND_START)

    def update(self, current: float) -> list[SpawnRequest]:
        current %= DAY
        requests: list[SpawnRequest] = []
        if self.previous_time is None:
            self.previous_time = current
            return requests
        if current < self.previous_time:
            self._reset_day()

        scheduled = (
            (
                "morning_rush",
                8 * HOUR + 45 * MINUTE,
                lambda: (9 * HOUR,) * 10,
            ),
            (
                "lunch",
                12 * HOUR,
                lambda: self._random_returns(12 * HOUR, 8, 30, 40),
            ),
            (
                "afternoon",
                13 * HOUR,
                lambda: self._random_returns(13 * HOUR, 4, 30, 40),
            ),
            (
                "evening_rush",
                17 * HOUR,
                lambda: (17 * HOUR + 30 * MINUTE,) * 10,
            ),
        )
        for label, start, make_returns in scheduled:
            if label not in self.fired and self._crossed(start, current):
                requests.append(SpawnRequest(label, make_returns()))
                self.fired.add(label)

        while self.next_background < BACKGROUND_END and self._crossed(self.next_background, current):
            start = self.next_background
            count = self.rng.randint(1, 3)
            requests.append(
                SpawnRequest("background", self._random_returns(start, count, 30, 60))
            )
            self.next_background = self._next_background_after(start)

        self.previous_time = current
        return requests
