"""Caso de uso: obter a liturgia de um dia, buscando na fonte externa só
quando o cache não tem — a única vez por dia que a rede é realmente usada.
"""

from __future__ import annotations

from datetime import date

from app.domain.liturgy.entities import DailyLiturgy
from app.domain.liturgy.gateway import LiturgyExternalGateway
from app.domain.liturgy.repository import DailyLiturgyRepository


class GetDailyLiturgyUseCase:
    """Cache-aside: lê do repositório; em cache-miss, busca no gateway,
    grava no repositório e devolve. Uma falha do gateway já chega aqui como
    `LiturgyFetchError` (o gateway que traduz o erro de rede/parsing — ver
    `app.infrastructure.liturgy.http_gateway`), então não há nada pra este
    método capturar."""

    def __init__(
        self,
        repository: DailyLiturgyRepository,
        gateway: LiturgyExternalGateway,
    ) -> None:
        self._repository = repository
        self._gateway = gateway

    async def execute(self, day: date) -> DailyLiturgy:
        cached = await self._repository.get_cached(day)
        if cached is not None:
            return cached

        liturgy = await self._gateway.fetch(day)

        # `save` não impede que duas requisições no mesmo cache-miss façam a
        # mesma gravação (ver `PostgresDailyLiturgyRepository.save`,
        # `ON CONFLICT DO NOTHING`) — a segunda só perde a própria gravação e
        # segue com o valor que já buscou.
        await self._repository.save(day, liturgy)
        return liturgy
