"""Resumo do painel de métricas: período, comparação e rankings."""

from __future__ import annotations

from datetime import date, timedelta

from app.application.metrics.summary import get_summary
from app.domain.metrics.entities import NewHit
from app.infrastructure.metrics.in_memory_repository import InMemoryMetricsRepository

TODAY = date(2026, 11, 19)


def _hit(day: date, visitor: str, path: str = "/", **extra: object) -> NewHit:
    base = {
        "day": day,
        "kind": "pagina",
        "path": path,
        "event": None,
        "referrer": None,
        "device": "celular",
        "visitor": visitor,
    }
    return NewHit(**{**base, **extra})  # type: ignore[arg-type]


async def test_should_fill_every_day_and_compare_with_the_previous_period() -> None:
    repo = InMemoryMetricsRepository()
    for hit in [
        _hit(TODAY, "a", "/santos"),
        _hit(TODAY, "a", "/oracoes"),
        _hit(TODAY, "b", "/santos", referrer="google.com", device="computador"),
        _hit(TODAY - timedelta(days=2), "a", "/", referrer="google.com"),
        _hit(TODAY, "b", "/velas", kind="evento", event="candle_lit"),
        # Período anterior (7 dias antes): uma visita.
        _hit(TODAY - timedelta(days=8), "c"),
    ]:
        await repo.record(hit)

    summary = await get_summary(repo, today=TODAY, days=7)

    assert (summary.start, summary.end) == (TODAY - timedelta(days=6), TODAY)
    assert len(summary.days) == 7
    assert summary.days[-1].visitors == 2 and summary.days[-1].views == 3
    assert summary.days[0].visitors == 0  # dia sem visita aparece zerado
    # "a" volta em dois dias diferentes: conta como visitante em cada dia.
    assert (summary.visitors, summary.views) == (3, 4)
    assert (summary.previous_visitors, summary.previous_views) == (1, 1)
    assert summary.top_pages[0].name == "/santos" and summary.top_pages[0].count == 2
    assert [(r.name, r.count) for r in summary.top_referrers] == [("google.com", 2)]
    assert [(r.name, r.count) for r in summary.events] == [("candle_lit", 1)]
    assert {r.name for r in summary.devices} == {"celular", "computador"}


async def test_should_accept_only_sane_periods() -> None:
    repo = InMemoryMetricsRepository()
    assert len((await get_summary(repo, today=TODAY, days=0)).days) == 1
    assert len((await get_summary(repo, today=TODAY, days=9999)).days) == 365
