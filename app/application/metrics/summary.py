"""Resumo do painel: o período pedido, o período anterior do mesmo tamanho e rankings."""

from __future__ import annotations

from datetime import date, timedelta

from app.domain.metrics.entities import DayCount, MetricsSummary
from app.domain.metrics.repository import MetricsRepository

MAX_DAYS = 365
TOP = 10


async def get_summary(
    repo: MetricsRepository, *, today: date, days: int
) -> MetricsSummary:
    days = min(max(days, 1), MAX_DAYS)
    start = today - timedelta(days=days - 1)
    previous_end = start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=days - 1)

    by_day = {d.day: d for d in await repo.daily(start, today)}
    # Dia sem visita aparece zerado: o gráfico precisa de todos os dias.
    filled = [
        by_day.get(day, DayCount(day=day, visitors=0, views=0))
        for day in (start + timedelta(days=i) for i in range(days))
    ]
    visitors, views = await repo.totals(start, today)
    previous_visitors, previous_views = await repo.totals(previous_start, previous_end)

    return MetricsSummary(
        start=start,
        end=today,
        days=filled,
        visitors=visitors,
        views=views,
        previous_visitors=previous_visitors,
        previous_views=previous_views,
        top_pages=await repo.top(start, today, "caminho", TOP),
        top_referrers=await repo.top(start, today, "origem", TOP),
        events=await repo.top(start, today, "evento", TOP),
        devices=await repo.top(start, today, "dispositivo", TOP),
    )
