"""Contrato de acesso às métricas; implementações em `app.infrastructure.metrics`."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from app.domain.metrics.entities import DayCount, NewHit, Ranked


class MetricsRepository(ABC):
    @abstractmethod
    async def record(self, hit: NewHit) -> None: ...

    @abstractmethod
    async def daily(self, start: date, end: date) -> list[DayCount]:
        """Visitantes e páginas vistas por dia, só dos dias com visita."""

    @abstractmethod
    async def totals(self, start: date, end: date) -> tuple[int, int]:
        """(visitantes, páginas vistas) do período. Visitante é contado por dia."""

    @abstractmethod
    async def top(self, start: date, end: date, field: str, limit: int) -> list[Ranked]:
        """Ranking de `caminho`, `origem`, `evento` ou `dispositivo`."""
