"""Testes HTTP da liturgia diária: cache, 503 sem banco e 503 de fonte
externa fora do ar. Nenhum teste toca a rede — o gateway real
(`HttpLiturgiaGateway`) nunca é chamado, só um fake injetado em
`app.state.liturgia_gateway`."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterator
from dataclasses import dataclass
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.domain.liturgia.entities import LiturgiaDiaria
from app.domain.liturgia.gateway import LiturgiaExternalGateway
from app.infrastructure.liturgia.http_gateway import parse_liturgia
from app.infrastructure.liturgia.in_memory_repository import (
    InMemoryLiturgiaDiariaRepository,
)
from app.main import app
from tests.infrastructure.test_liturgia_http_gateway import PAYLOAD_DIA_DE_SEMANA


@dataclass
class _FakeGateway(LiturgiaExternalGateway):
    """Injeta um `fetch` arbitrário sem precisar de rede nem de uma classe
    de teste nova a cada cenário."""

    fetch_fn: Callable[[date], Awaitable[LiturgiaDiaria]]

    async def fetch(self, dia: date) -> LiturgiaDiaria:
        return await self.fetch_fn(dia)


@pytest.fixture()
def client() -> Iterator[TestClient]:
    """TestClient próprio (não o `module`-scoped de test_routers): cada
    teste aqui manipula `app.state.liturgia_repository`/`liturgia_gateway`,
    então precisa de isolamento por teste, não compartilhado."""
    with TestClient(app) as test_client:
        yield test_client


def test_should_return_503_when_database_not_configured(client: TestClient) -> None:
    """Sem `DATABASE_URL`, o lifespan real deixa `liturgia_repository` em `None`."""
    # Given
    client.app.state.liturgia_repository = None

    # When
    response = client.get("/api/liturgia-diaria")

    # Then
    assert response.status_code == 503
    assert response.json()["code"] == "LITURGIA_INDISPONIVEL"


def test_should_return_liturgia_for_a_specific_date(client: TestClient) -> None:
    # Given
    async def fake_fetch(dia: date) -> LiturgiaDiaria:
        return parse_liturgia(dia, PAYLOAD_DIA_DE_SEMANA)

    client.app.state.liturgia_repository = InMemoryLiturgiaDiariaRepository()
    client.app.state.liturgia_gateway = _FakeGateway(fake_fetch)

    # When
    response = client.get("/api/liturgia-diaria", params={"data": "2026-09-08"})

    # Then
    assert response.status_code == 200
    body = response.json()
    assert body["data"] == "2026-09-08"
    assert body["evangelho"]["referencia"] == "Evangelho de Jesus Cristo segundo São Mateus 1, 1-16.18-23"


def test_should_cache_and_call_gateway_only_once_per_date(client: TestClient) -> None:
    # Given
    chamadas = 0

    async def fake_fetch(dia: date) -> LiturgiaDiaria:
        nonlocal chamadas
        chamadas += 1
        return parse_liturgia(dia, PAYLOAD_DIA_DE_SEMANA)

    client.app.state.liturgia_repository = InMemoryLiturgiaDiariaRepository()
    client.app.state.liturgia_gateway = _FakeGateway(fake_fetch)

    # When
    first = client.get("/api/liturgia-diaria", params={"data": "2026-09-08"})
    second = client.get("/api/liturgia-diaria", params={"data": "2026-09-08"})

    # Then
    assert first.status_code == second.status_code == 200
    assert chamadas == 1


def test_should_return_503_when_external_source_fails(client: TestClient) -> None:
    # Given
    async def failing_fetch(dia: date) -> LiturgiaDiaria:
        raise RuntimeError("fonte externa fora do ar")

    client.app.state.liturgia_repository = InMemoryLiturgiaDiariaRepository()
    client.app.state.liturgia_gateway = _FakeGateway(failing_fetch)

    # When
    response = client.get("/api/liturgia-diaria", params={"data": "2026-09-08"})

    # Then
    assert response.status_code == 503
    assert response.json()["code"] == "LITURGIA_INDISPONIVEL"


def test_should_default_to_todays_date_when_no_date_given(client: TestClient) -> None:
    # Given
    recebido: list[date] = []

    async def fake_fetch(dia: date) -> LiturgiaDiaria:
        recebido.append(dia)
        return parse_liturgia(dia, PAYLOAD_DIA_DE_SEMANA)

    client.app.state.liturgia_repository = InMemoryLiturgiaDiariaRepository()
    client.app.state.liturgia_gateway = _FakeGateway(fake_fetch)

    # When
    response = client.get("/api/liturgia-diaria")

    # Then
    assert response.status_code == 200
    assert len(recebido) == 1
    assert recebido[0] == date.fromisoformat(response.json()["data"])
