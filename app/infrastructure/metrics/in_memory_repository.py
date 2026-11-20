"""Repositório de métricas em memória, para os testes (mesmas regras do Postgres)."""

from __future__ import annotations

from collections import Counter
from datetime import date

from app.domain.metrics.entities import DayCount, NewHit, Ranked
from app.domain.metrics.repository import MetricsRepository

_FIELD = {
    "caminho": "path",
    "origem": "referrer",
    "evento": "event",
    "dispositivo": "device",
}


class InMemoryMetricsRepository(MetricsRepository):
    def __init__(self) -> None:
        self.hits: list[NewHit] = []

    async def record(self, hit: NewHit) -> None:
        self.hits.append(hit)

    def _between(self, start: date, end: date) -> list[NewHit]:
        return [h for h in self.hits if start <= h.day <= end]

    async def daily(self, start: date, end: date) -> list[DayCount]:
        days = sorted({h.day for h in self._between(start, end)})
        return [
            DayCount(
                day=d,
                visitors=len({h.visitor for h in self.hits if h.day == d}),
                views=sum(1 for h in self.hits if h.day == d and h.kind == "pagina"),
            )
            for d in days
        ]

    async def totals(self, start: date, end: date) -> tuple[int, int]:
        hits = self._between(start, end)
        visitors = len({(h.day, h.visitor) for h in hits})
        return visitors, sum(1 for h in hits if h.kind == "pagina")

    async def top(self, start: date, end: date, field: str, limit: int) -> list[Ranked]:
        attr = _FIELD[field]
        kind = "evento" if field == "evento" else "pagina"
        counter = Counter(
            getattr(h, attr)
            for h in self._between(start, end)
            if h.kind == kind and getattr(h, attr)
        )
        ordered = sorted(counter.items(), key=lambda item: (-item[1], item[0]))
        return [Ranked(name=name, count=count) for name, count in ordered[:limit]]
