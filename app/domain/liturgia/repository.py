"""Contrato de cache da liturgia diária — só cache, não busca externa.

Separado do gateway (`app.domain.liturgia.gateway`) de propósito: cache é
uma responsabilidade (guardar/ler o que já foi buscado), buscar na fonte
externa é outra (rede, parsing de um formato de terceiro). A classe antiga
misturava as duas; quem decide QUANDO usar cada uma é o use case
(`ObterLiturgiaDoDiaUseCase`), não o repositório.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from app.domain.liturgia.entities import LiturgiaDiaria


class LiturgiaDiariaRepository(ABC):
    """Interface que o use case depende — implementação é um detalhe."""

    @abstractmethod
    async def get_cached(self, dia: date) -> LiturgiaDiaria | None: ...

    @abstractmethod
    async def save(self, dia: date, liturgia: LiturgiaDiaria) -> None: ...
