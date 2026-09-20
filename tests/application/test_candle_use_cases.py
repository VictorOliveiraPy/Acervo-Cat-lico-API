"""Testes dos use cases de velas isolados da camada HTTP — nenhum destes
sobe um `TestClient` nem conhece FastAPI, só o repositório fake."""

from __future__ import annotations

from app.application.candles.light_candle_use_case import LightCandleUseCase
from app.application.candles.list_candles_use_case import ListCandlesUseCase
from app.domain.candles.entities import CandleType, NewCandle
from app.infrastructure.candles.in_memory_repository import InMemoryCandleRepository


async def test_should_return_created_candle_with_assigned_id() -> None:
    # Given
    repo = InMemoryCandleRepository()
    use_case = LightCandleUseCase(repo)
    new_candle = NewCandle(name="Maria", candle_type=CandleType.JESUS, intention="Por todos")

    # When
    candle = await use_case.execute(new_candle)

    # Then
    assert candle.id == 1
    assert candle.name == "Maria"
    assert candle.intention == "Por todos"


async def test_should_list_page_with_total_count_when_more_items_than_limit() -> None:
    # Given
    repo = InMemoryCandleRepository()
    light = LightCandleUseCase(repo)
    for name in ["Primeira", "Segunda", "Terceira"]:
        await light.execute(NewCandle(name=name, candle_type=CandleType.SAINT_BENEDICT))

    # When
    page = await ListCandlesUseCase(repo).execute(limit=2, offset=0)

    # Then
    assert page.total == 3
    assert [candle.name for candle in page.items] == ["Terceira", "Segunda"]
