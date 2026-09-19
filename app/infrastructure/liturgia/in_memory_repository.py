"""Fake do cache de liturgia — mesma interface, sem Postgres."""

from __future__ import annotations

from datetime import date

from app.domain.liturgia.entities import LiturgiaDiaria
from app.domain.liturgia.repository import LiturgiaDiariaRepository


class InMemoryLiturgiaDiariaRepository(LiturgiaDiariaRepository):
    def __init__(self) -> None:
        self._cache: dict[date, LiturgiaDiaria] = {}

    async def get_cached(self, dia: date) -> LiturgiaDiaria | None:
        return self._cache.get(dia)

    async def save(self, dia: date, liturgia: LiturgiaDiaria) -> None:
        self._cache[dia] = liturgia
