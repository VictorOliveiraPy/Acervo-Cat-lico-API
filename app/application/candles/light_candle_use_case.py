"""Caso de uso: acender uma vela no mural público."""

from __future__ import annotations

from app.domain.candles.entities import Candle, NewCandle
from app.domain.candles.repository import CandleRepository


class LightCandleUseCase:
    """Orquestra a criação de uma vela — hoje é uma passagem direta ao
    repositório, mas é aqui (não no router) que uma regra de negócio nova
    sobre acender uma vela entraria."""

    def __init__(self, repository: CandleRepository) -> None:
        self._repository = repository

    async def execute(self, new_candle: NewCandle) -> Candle:
        return await self._repository.create(new_candle)
