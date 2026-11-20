"""O repositório de métricas contra um Postgres de verdade, com o mesmo cenário do
repositório em memória. Só roda com `TEST_DATABASE_URL` (ex.: um Postgres em Docker)."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import date, timedelta

import pytest

from app.application.metrics.summary import get_summary
from app.domain.metrics.entities import NewHit
from app.infrastructure.metrics.in_memory_repository import InMemoryMetricsRepository
from app.infrastructure.metrics.postgres_repository import PostgresMetricsRepository

DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="sem TEST_DATABASE_URL")

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


HITS = [
    _hit(TODAY, "a", "/santos"),
    _hit(TODAY, "a", "/oracoes"),
    _hit(TODAY, "b", "/santos", referrer="google.com", device="computador"),
    _hit(TODAY - timedelta(days=2), "a", "/", referrer="google.com"),
    _hit(TODAY, "b", "/velas", kind="evento", event="candle_lit"),
    _hit(TODAY - timedelta(days=8), "c"),
]


@pytest.fixture()
async def pool() -> AsyncIterator[object]:
    import asyncpg

    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=2)
    await pool.execute("DROP TABLE IF EXISTS metricas")
    await PostgresMetricsRepository.create_schema(pool)
    yield pool
    await pool.execute("DROP TABLE IF EXISTS metricas")
    await pool.close()


async def test_postgres_gives_the_same_summary_as_memory(pool: object) -> None:
    postgres = PostgresMetricsRepository(pool)  # type: ignore[arg-type]
    memory = InMemoryMetricsRepository()
    for hit in HITS:
        await postgres.record(hit)
        await memory.record(hit)

    assert await get_summary(postgres, today=TODAY, days=7) == await get_summary(
        memory, today=TODAY, days=7
    )


async def test_schema_creation_drops_rows_past_retention(pool: object) -> None:
    repo = PostgresMetricsRepository(pool)  # type: ignore[arg-type]
    await repo.record(_hit(date.today() - timedelta(days=500), "velho"))
    await repo.record(_hit(date.today(), "novo"))
    await PostgresMetricsRepository.create_schema(pool)  # type: ignore[arg-type]
    assert (await repo.totals(date(2000, 1, 1), date.today()))[0] == 1
