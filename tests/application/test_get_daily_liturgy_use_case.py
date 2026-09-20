"""Testes do use case isolados da camada HTTP — provam a regra de cache
(busca no gateway só uma vez por dia) sem `TestClient` nem FastAPI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pytest

from app.application.liturgy.get_daily_liturgy_use_case import GetDailyLiturgyUseCase
from app.domain.liturgy.entities import DailyLiturgy, LiturgicalReading
from app.domain.liturgy.exceptions import LiturgyFetchError
from app.domain.liturgy.gateway import LiturgyExternalGateway
from app.infrastructure.liturgy.in_memory_repository import (
    InMemoryDailyLiturgyRepository,
)

_READING = LiturgicalReading(reference="Jo 1, 1-5", text="No princípio era o Verbo...")


def _sample_liturgy(day: date) -> DailyLiturgy:
    return DailyLiturgy(
        date=day,
        liturgical_color="branco",
        celebration="Exemplo",
        first_reading=_READING,
        psalm=_READING,
        gospel=_READING,
        source="teste",
    )


@dataclass
class _CountingGateway(LiturgyExternalGateway):
    """Conta quantas vezes `fetch` foi chamado, sem tocar rede."""

    calls: int = 0
    should_fail: bool = False

    async def fetch(self, day: date) -> DailyLiturgy:
        self.calls += 1
        if self.should_fail:
            raise LiturgyFetchError()
        return _sample_liturgy(day)


async def test_should_fetch_from_gateway_only_once_when_called_twice_for_same_day() -> None:
    # Given
    repo = InMemoryDailyLiturgyRepository()
    gateway = _CountingGateway()
    use_case = GetDailyLiturgyUseCase(repo, gateway)
    day = date(2026, 9, 19)

    # When
    first = await use_case.execute(day)
    second = await use_case.execute(day)

    # Then
    assert gateway.calls == 1
    assert first == second


async def test_should_propagate_liturgy_fetch_error_when_gateway_fails() -> None:
    """O use case não traduz o erro — o gateway (`HttpLiturgyGateway`) que já
    entrega `LiturgyFetchError` pronta para o handler global."""
    # Given
    repo = InMemoryDailyLiturgyRepository()
    gateway = _CountingGateway(should_fail=True)
    use_case = GetDailyLiturgyUseCase(repo, gateway)

    # When / Then
    with pytest.raises(LiturgyFetchError) as exc_info:
        await use_case.execute(date(2026, 9, 19))
    assert exc_info.value.code == "LITURGIA_INDISPONIVEL"
