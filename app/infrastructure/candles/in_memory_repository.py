"""Fake do repositório de velas — mesma interface, sem rede nem Postgres.

Usado nos testes de `application`/`interface`: nenhum precisa de um
Postgres de verdade rodando.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.domain.candles.entities import Candle, NewCandle
from app.domain.candles.repository import CandleRepository


class InMemoryCandleRepository(CandleRepository):
    def __init__(self) -> None:
        self._items: list[Candle] = []
        self._next_id = 1

    async def create(self, new_candle: NewCandle) -> Candle:
        candle = Candle(
            id=self._next_id,
            name=new_candle.name,
            intention=new_candle.intention,
            candle_type=new_candle.candle_type,
            city=new_candle.city,
            state=new_candle.state,
            created_at=datetime.now(UTC),
        )
        self._items.insert(0, candle)
        self._next_id += 1
        return candle

    async def list_page(self, limit: int, offset: int) -> tuple[list[Candle], int]:
        total = len(self._items)
        return self._items[offset : offset + limit], total
