"""Os repositórios do estúdio, em memória e no Postgres, com o mesmo contrato.

O Postgres só roda com `TEST_DATABASE_URL` (ex.: um Postgres em Docker)."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest

from app.domain.studio.entities import NewVideoRequest, Reel
from app.infrastructure.studio import postgres_repository as pg
from app.infrastructure.studio.in_memory_repository import (
    InMemoryReelRepository,
    InMemoryVideoRequestRepository,
)

DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
BACKENDS = [
    "memoria",
    pytest.param(
        "postgres",
        marks=pytest.mark.skipif(not DATABASE_URL, reason="sem TEST_DATABASE_URL"),
    ),
]
T0 = datetime(2026, 11, 1, tzinfo=UTC)


def _reel(
    slug: str, *, minutes: int, theme: str = "santos", published: bool = True
) -> Reel:
    return Reel(
        slug=slug,
        title=slug.title(),
        caption="",
        theme=theme,
        width=720,
        height=1280,
        video_url=f"https://cdn/reels/{slug}.mp4",
        cover_url=f"/reels/{slug}.jpg",
        published=published,
        created_at=T0 + timedelta(minutes=minutes),
    )


@pytest.fixture(params=BACKENDS)
async def repos(request: pytest.FixtureRequest) -> AsyncIterator[tuple[object, object]]:
    if request.param == "memoria":
        yield InMemoryReelRepository(), InMemoryVideoRequestRepository()
        return
    import asyncpg

    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=2)
    await pool.execute("DROP TABLE IF EXISTS reels, pedidos_video")
    await pg.create_schema(pool)
    yield pg.PostgresReelRepository(pool), pg.PostgresVideoRequestRepository(pool)
    await pool.execute("DROP TABLE IF EXISTS reels, pedidos_video")
    await pool.close()


async def test_reels_list_newest_first_with_filters(repos: tuple) -> None:
    reels, _ = repos
    await reels.create(_reel("antigo", minutes=1))
    await reels.create(_reel("novo", minutes=3, theme="missa"))
    await reels.create(_reel("rascunho", minutes=5, published=False))

    published, total = await reels.list(
        theme=None, only_published=True, limit=10, offset=0
    )
    assert [r.slug for r in published] == ["novo", "antigo"] and total == 2
    everything, total_all = await reels.list(
        theme=None, only_published=False, limit=1, offset=0
    )
    assert [r.slug for r in everything] == ["rascunho"] and total_all == 3
    by_theme, _ = await reels.list(
        theme="missa", only_published=True, limit=10, offset=0
    )
    assert [r.slug for r in by_theme] == ["novo"]


async def test_reels_create_update_delete(repos: tuple) -> None:
    reels, _ = repos
    await reels.create(_reel("sao-jose", minutes=1))
    with pytest.raises(KeyError):
        await reels.create(_reel("sao-jose", minutes=2))

    updated = await reels.update("sao-jose", {"title": "São José", "published": False})
    assert updated is not None and (updated.title, updated.published) == (
        "São José",
        False,
    )
    assert await reels.update("nao-existe", {"title": "x"}) is None
    assert await reels.delete("sao-jose") is True
    assert await reels.delete("sao-jose") is False
    assert await reels.get("sao-jose") is None


async def test_requests_queue_in_order_and_claim_once(repos: tuple) -> None:
    _, requests = repos
    first = await requests.create(
        NewVideoRequest("Confissão", "O padre pode contar?", "", "cinema")
    )
    await requests.create(NewVideoRequest("Missa", "", "", "meme"))

    claimed = await requests.claim_next()
    assert (
        claimed is not None and claimed.id == first.id and claimed.status == "gerando"
    )
    second = await requests.claim_next()
    assert second is not None and second.theme == "Missa"
    assert await requests.claim_next() is None

    done = await requests.update(
        first.id, status="pronto", stage="Pronto", progress=100, slug="confissao"
    )
    assert done is not None and (done.status, done.slug) == ("pronto", "confissao")
    assert [r.id for r in await requests.list_recent(10)] == [second.id, first.id]
