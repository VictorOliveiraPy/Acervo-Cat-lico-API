"""Contrato de acesso a dados do mural de velas — sem implementação aqui.

Duas implementações vivem em `app.infrastructure.candles`:
`PostgresCandleRepository` (produção) e `InMemoryCandleRepository` (testes) —
nenhum teste de `application`/`interface` precisa de um Postgres de verdade
rodando.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.candles.entities import Candle, NewCandle


class CandleRepository(ABC):
    """Interface que os use cases dependem — implementação é um detalhe."""

    @abstractmethod
    async def create(self, new_candle: NewCandle) -> Candle: ...

    @abstractmethod
    async def list_page(self, limit: int, offset: int) -> tuple[list[Candle], int]: ...
