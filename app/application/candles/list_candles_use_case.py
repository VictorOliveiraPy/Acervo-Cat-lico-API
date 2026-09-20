"""Caso de uso: listar o mural de velas, mais recentes primeiro."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.candles.entities import Candle
from app.domain.candles.repository import CandleRepository


@dataclass(frozen=True, slots=True)
class CandlePage:
    """Resultado paginado — `total` é a contagem inteira, não só a página."""

    items: list[Candle]
    total: int


class ListCandlesUseCase:
    """Devolve uma página do mural — a ordenação (mais recentes primeiro)
    é responsabilidade do repositório, que sabe como ordenar de forma
    eficiente na fonte de dados real."""

    def __init__(self, repository: CandleRepository) -> None:
        self._repository = repository

    async def execute(self, limit: int, offset: int) -> CandlePage:
        items, total = await self._repository.list_page(limit=limit, offset=offset)
        return CandlePage(items=items, total=total)
