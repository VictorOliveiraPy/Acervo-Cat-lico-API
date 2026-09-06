"""Testes do mural de velas: 503 sem banco configurado, CRUD básico com o
repositório em memória, validação e rate limit."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.velas_repository import InMemoryVelasRepository
from app.velas_router import _rate_limiter


@pytest.fixture()
def client() -> Iterator[TestClient]:
    """TestClient próprio (não o `module`-scoped de test_routers): cada
    teste aqui manipula `app.state.velas_repository`, então precisa de
    isolamento por teste, não compartilhado."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def reset_rate_limiter() -> Iterator[None]:
    """O limitador é um singleton do módulo — sem isto, um teste "gasta" a
    janela de outro."""
    _rate_limiter._last_seen.clear()
    yield
    _rate_limiter._last_seen.clear()


def test_should_return_503_when_database_not_configured(client: TestClient) -> None:
    """Sem `DATABASE_URL`, o lifespan real deixa `velas_repository` em `None`."""
    # Given
    client.app.state.velas_repository = None

    # When
    response = client.get("/api/velas")

    # Then
    assert response.status_code == 503
    assert response.json()["code"] == "VELAS_INDISPONIVEL"


def test_should_reject_creation_when_database_not_configured(
    client: TestClient,
) -> None:
    # Given
    client.app.state.velas_repository = None

    # When
    response = client.post(
        "/api/velas", json={"nome": "Maria", "tipo": "branca"}
    )

    # Then
    assert response.status_code == 503


def test_should_create_and_list_vela_when_repository_is_configured(
    client: TestClient,
) -> None:
    # Given
    client.app.state.velas_repository = InMemoryVelasRepository()

    # When
    create_response = client.post(
        "/api/velas",
        json={"nome": "Maria", "intencao": "Pela saúde da família", "tipo": "branca"},
    )

    # Then
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["nome"] == "Maria"
    assert created["intencao"] == "Pela saúde da família"
    assert created["tipo"] == "branca"
    assert created["id"] == 1

    # When
    list_response = client.get("/api/velas")

    # Then
    assert list_response.status_code == 200
    body = list_response.json()
    assert body["total"] == 1
    assert body["itens"][0]["nome"] == "Maria"


def test_should_accept_creation_without_intention(client: TestClient) -> None:
    # Given
    client.app.state.velas_repository = InMemoryVelasRepository()

    # When
    response = client.post(
        "/api/velas", json={"nome": "João", "tipo": "dourada"}
    )

    # Then
    assert response.status_code == 201
    assert response.json()["intencao"] is None


def test_should_reject_blank_name(client: TestClient) -> None:
    # Given
    client.app.state.velas_repository = InMemoryVelasRepository()

    # When
    response = client.post("/api/velas", json={"nome": "   ", "tipo": "branca"})

    # Then
    assert response.status_code == 422


def test_should_reject_unknown_candle_type(client: TestClient) -> None:
    # Given
    client.app.state.velas_repository = InMemoryVelasRepository()

    # When
    response = client.post(
        "/api/velas", json={"nome": "Ana", "tipo": "verde-limao"}
    )

    # Then
    assert response.status_code == 422


def test_should_rate_limit_second_creation_from_same_client(
    client: TestClient,
) -> None:
    # Given
    client.app.state.velas_repository = InMemoryVelasRepository()
    first = client.post("/api/velas", json={"nome": "Pedro", "tipo": "azul"})
    assert first.status_code == 201

    # When
    second = client.post("/api/velas", json={"nome": "Pedro", "tipo": "azul"})

    # Then
    assert second.status_code == 429
    assert second.json()["code"] == "RATE_LIMITED"


def test_should_paginate_velas_newest_first(client: TestClient) -> None:
    # Given
    repo = InMemoryVelasRepository()
    client.app.state.velas_repository = repo
    import asyncio

    from app.velas_models import TipoVela, VelaCreate

    for nome in ["Primeira", "Segunda", "Terceira"]:
        asyncio.run(repo.create(VelaCreate(nome=nome, tipo=TipoVela.ROXA)))

    # When
    response = client.get("/api/velas", params={"limit": 2, "offset": 0})

    # Then
    body = response.json()
    assert body["total"] == 3
    assert [item["nome"] for item in body["itens"]] == ["Terceira", "Segunda"]
