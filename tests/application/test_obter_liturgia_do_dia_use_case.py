"""Testes do use case isolados da camada HTTP — provam a regra de cache
(busca no gateway só uma vez por dia) sem `TestClient` nem FastAPI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pytest

from app.application.liturgia.obter_liturgia_do_dia_use_case import (
    ObterLiturgiaDoDiaUseCase,
)
from app.core.exceptions import ServiceUnavailableException
from app.domain.liturgia.entities import LeituraLiturgica, LiturgiaDiaria
from app.domain.liturgia.gateway import LiturgiaExternalGateway
from app.infrastructure.liturgia.in_memory_repository import (
    InMemoryLiturgiaDiariaRepository,
)

_LEITURA = LeituraLiturgica(referencia="Jo 1, 1-5", texto="No princípio era o Verbo...")


def _liturgia_exemplo(dia: date) -> LiturgiaDiaria:
    return LiturgiaDiaria(
        data=dia,
        cor_liturgica="branco",
        celebracao="Exemplo",
        primeira_leitura=_LEITURA,
        salmo=_LEITURA,
        evangelho=_LEITURA,
        fonte="teste",
    )


@dataclass
class _CountingGateway(LiturgiaExternalGateway):
    """Conta quantas vezes `fetch` foi chamado, sem tocar rede."""

    chamadas: int = 0
    falhar: bool = False

    async def fetch(self, dia: date) -> LiturgiaDiaria:
        self.chamadas += 1
        if self.falhar:
            raise RuntimeError("fonte externa fora do ar")
        return _liturgia_exemplo(dia)


async def test_should_fetch_from_gateway_only_once_when_called_twice_for_same_day() -> None:
    # Given
    repo = InMemoryLiturgiaDiariaRepository()
    gateway = _CountingGateway()
    use_case = ObterLiturgiaDoDiaUseCase(repo, gateway)
    dia = date(2026, 9, 19)

    # When
    primeira = await use_case.execute(dia)
    segunda = await use_case.execute(dia)

    # Then
    assert gateway.chamadas == 1
    assert primeira == segunda


async def test_should_raise_service_unavailable_when_gateway_fails() -> None:
    # Given
    repo = InMemoryLiturgiaDiariaRepository()
    gateway = _CountingGateway(falhar=True)
    use_case = ObterLiturgiaDoDiaUseCase(repo, gateway)

    # When / Then
    with pytest.raises(ServiceUnavailableException) as exc_info:
        await use_case.execute(date(2026, 9, 19))
    assert exc_info.value.code == "LITURGIA_INDISPONIVEL"
