"""Caso de uso: obter a liturgia de um dia, buscando na fonte externa só
quando o cache não tem — a única vez por dia que a rede é realmente usada.
"""

from __future__ import annotations

import logging
from datetime import date

from app.core.exceptions import ServiceUnavailableException
from app.domain.liturgia.entities import LiturgiaDiaria
from app.domain.liturgia.gateway import LiturgiaExternalGateway
from app.domain.liturgia.repository import LiturgiaDiariaRepository

logger = logging.getLogger(__name__)


class ObterLiturgiaDoDiaUseCase:
    """Cache-aside: lê do repositório; em cache-miss, busca no gateway,
    grava no repositório e devolve. Uma falha do gateway (rede, HTTP 5xx,
    JSON malformado) vira `ServiceUnavailableException` — nunca um 500 cru
    pro cliente por causa de uma fonte de terceiro fora do ar."""

    def __init__(
        self,
        repository: LiturgiaDiariaRepository,
        gateway: LiturgiaExternalGateway,
    ) -> None:
        self._repository = repository
        self._gateway = gateway

    async def execute(self, dia: date) -> LiturgiaDiaria:
        cached = await self._repository.get_cached(dia)
        if cached is not None:
            return cached

        try:
            liturgia = await self._gateway.fetch(dia)
        except Exception as exc:
            logger.warning("Falha ao buscar liturgia de %s: %s", dia, exc)
            raise ServiceUnavailableException(
                message="Não foi possível buscar a liturgia de hoje. Tente novamente em instantes.",
                code="LITURGIA_INDISPONIVEL",
            ) from exc

        # `save` não impede que duas requisições no mesmo cache-miss façam a
        # mesma gravação (ver `PostgresLiturgiaDiariaRepository.save`,
        # `ON CONFLICT DO NOTHING`) — a segunda só perde a própria escrita e
        # segue com o valor que já buscou.
        await self._repository.save(dia, liturgia)
        return liturgia
