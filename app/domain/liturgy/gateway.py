"""Contrato de busca da liturgia numa fonte externa — sem implementação.

A implementação real (`app.infrastructure.liturgy.http_gateway`) sabe o
formato JSON específico do agregador de terceiros atual; o domínio só
conhece "dado um dia, devolva a `DailyLiturgy` daquele dia" — trocar de
fonte externa no futuro é trocar só a implementação, ninguém mais muda.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from app.domain.liturgy.entities import DailyLiturgy


class LiturgyExternalGateway(ABC):
    """Interface que o use case depende — implementação é um detalhe."""

    @abstractmethod
    async def fetch(self, day: date) -> DailyLiturgy: ...
