"""Fake do cache de liturgia — mesma interface, sem Postgres."""

from __future__ import annotations

from datetime import date

from app.domain.liturgy.entities import DailyLiturgy
from app.domain.liturgy.repository import DailyLiturgyRepository


class InMemoryDailyLiturgyRepository(DailyLiturgyRepository):
    def __init__(self) -> None:
        self._cache: dict[date, DailyLiturgy] = {}

    async def get_cached(self, day: date) -> DailyLiturgy | None:
        return self._cache.get(day)

    async def save(self, day: date, liturgy: DailyLiturgy) -> None:
        self._cache[day] = liturgy
