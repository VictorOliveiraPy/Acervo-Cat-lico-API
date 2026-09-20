"""Contrato de cache da liturgia diária — só cache, não busca externa.

Separado do gateway (`app.domain.liturgy.gateway`) de propósito: cache é
uma responsabilidade (guardar/ler o que já foi buscado), buscar na fonte
externa é outra (rede, parsing de um formato de terceiro). A classe antiga
misturava as duas; quem decide QUANDO usar cada uma é o use case
(`GetDailyLiturgyUseCase`), não o repositório.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from app.domain.liturgy.entities import DailyLiturgy


class DailyLiturgyRepository(ABC):
    """Interface que o use case depende — implementação é um detalhe."""

    @abstractmethod
    async def get_cached(self, day: date) -> DailyLiturgy | None: ...

    @abstractmethod
    async def save(self, day: date, liturgy: DailyLiturgy) -> None: ...
