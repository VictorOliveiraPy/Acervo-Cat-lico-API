"""Camadas da liturgia: fonte principal, secundária, e última liturgia salva."""

from __future__ import annotations

from dataclasses import replace
from datetime import date

import pytest

from app.application.liturgy.get_daily_liturgy_use_case import GetDailyLiturgyUseCase
from app.application.liturgy.prefetch_liturgy import prefetch_liturgy
from app.domain.liturgy.entities import DailyLiturgy, LiturgicalReading
from app.domain.liturgy.exceptions import LiturgyFetchError
from app.domain.liturgy.gateway import LiturgyExternalGateway
from app.infrastructure.liturgy.in_memory_repository import (
    InMemoryDailyLiturgyRepository,
)
from app.infrastructure.liturgy.railway_gateway import (
    FallbackLiturgyGateway,
    parse_railway_liturgy,
)

TODAY = date(2026, 10, 30)
READING = LiturgicalReading(reference="Jo 1,1", text="No princípio")
LITURGY = DailyLiturgy(
    date=TODAY,
    liturgical_color="Verde",
    celebration="Tempo Comum",
    first_reading=READING,
    psalm=READING,
    gospel=READING,
    source="teste",
)


class Failing(LiturgyExternalGateway):
    async def fetch(self, day: date) -> DailyLiturgy:
        raise LiturgyFetchError()


class Working(LiturgyExternalGateway):
    async def fetch(self, day: date) -> DailyLiturgy:
        return replace(LITURGY, date=day)


PAYLOAD = {
    "data": "30/10/2026",
    "liturgia": "6ª feira",
    "cor": "Verde",
    "leituras": {
        "primeiraLeitura": [{"referencia": "Rm 9,1-5", "texto": "Irmãos"}],
        "salmo": [{"referencia": "Sl 147", "refrao": "Glorifica", "texto": "Louva"}],
        "segundaLeitura": [],
        "evangelho": [{"referencia": "Lc 14,1-6", "texto": "Naquele tempo"}],
    },
}


def test_should_parse_the_source_format() -> None:
    liturgy = parse_railway_liturgy(TODAY, PAYLOAD)
    assert liturgy.gospel.reference == "Lc 14,1-6"
    assert liturgy.psalm.text == "Glorifica\nLouva"
    assert liturgy.second_reading is None


def test_should_refuse_a_response_for_another_day() -> None:
    with pytest.raises(ValueError):
        parse_railway_liturgy(date(2026, 10, 31), PAYLOAD)


async def test_should_use_the_secondary_source_when_the_main_one_fails() -> None:
    liturgy = await FallbackLiturgyGateway([Failing(), Working()]).fetch(TODAY)
    assert liturgy.date == TODAY


async def test_should_fail_only_when_every_source_fails() -> None:
    with pytest.raises(LiturgyFetchError):
        await FallbackLiturgyGateway([Failing(), Failing()]).fetch(TODAY)


async def test_should_show_the_last_saved_liturgy_when_the_sources_are_down() -> None:
    repo = InMemoryDailyLiturgyRepository()
    older = date(2026, 10, 28)
    await repo.save(older, replace(LITURGY, date=older))

    liturgy = await GetDailyLiturgyUseCase(repo, Failing()).execute(TODAY, allow_stale=True)

    assert liturgy.date == older


async def test_should_not_swap_the_day_of_an_explicit_date() -> None:
    repo = InMemoryDailyLiturgyRepository()
    await repo.save(date(2026, 10, 28), replace(LITURGY, date=date(2026, 10, 28)))
    with pytest.raises(LiturgyFetchError):
        await GetDailyLiturgyUseCase(repo, Failing()).execute(TODAY)


async def test_should_fail_when_nothing_was_ever_saved() -> None:
    with pytest.raises(LiturgyFetchError):
        await GetDailyLiturgyUseCase(
            InMemoryDailyLiturgyRepository(), Failing()
        ).execute(TODAY, allow_stale=True)


async def test_should_prefetch_today_and_the_next_seven_days() -> None:
    repo = InMemoryDailyLiturgyRepository()
    assert await prefetch_liturgy(repo, Working(), TODAY) == []
    assert await repo.get_cached(date(2026, 11, 6)) is not None
    assert await repo.get_cached(date(2026, 11, 7)) is None


async def test_should_report_the_days_it_could_not_fetch() -> None:
    missing = await prefetch_liturgy(InMemoryDailyLiturgyRepository(), Failing(), TODAY)
    assert len(missing) == 8
