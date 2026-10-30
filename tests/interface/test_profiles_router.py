"""Rotas do perfil e do ranking, com repositório em memória."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.infrastructure.profiles.in_memory_repository import InMemoryProfileRepository
from app.interface.profiles.router import get_profile_repository
from app.main import app

SECRET = "segredo-de-teste"
ANA = {"X-Internal-Secret": SECRET, "X-User-Sub": "google-ana"}
BIA = {"X-Internal-Secret": SECRET, "X-User-Sub": "google-bia"}


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setattr(settings, "internal_api_secret", SECRET)
    repo = InMemoryProfileRepository()
    app.dependency_overrides[get_profile_repository] = lambda: repo
    yield TestClient(app)
    app.dependency_overrides.pop(get_profile_repository, None)


def test_should_refuse_without_the_shared_secret(client: TestClient) -> None:
    response = client.post(
        "/api/perfil", json={"nome": "Ana"}, headers={"X-User-Sub": "google-ana"}
    )
    assert response.status_code == 401
    assert response.json()["code"] == "NAO_AUTORIZADO"


def test_should_answer_503_when_the_secret_is_not_configured(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "internal_api_secret", None)
    assert client.post("/api/perfil", json={"nome": "Ana"}, headers=ANA).status_code == 503


def test_should_create_once_and_keep_the_chosen_name(client: TestClient) -> None:
    assert client.post("/api/perfil", json={"nome": "Ana"}, headers=ANA).json()["pontos"] == 0
    client.put(
        "/api/perfil",
        json={"nome": "Ana Clara", "preferencias": ["santos"], "no_ranking": False},
        headers=ANA,
    )
    profile = client.post("/api/perfil", json={"nome": "Ana"}, headers=ANA).json()
    assert profile["nome"] == "Ana Clara"
    assert profile["preferencias"] == ["santos"]


def test_should_not_score_the_same_lesson_twice(client: TestClient) -> None:
    client.post("/api/perfil", json={"nome": "Ana"}, headers=ANA)
    client.post("/api/perfil/licoes", json={"licoes": ["a-criacao"]}, headers=ANA)
    profile = client.post(
        "/api/perfil/licoes", json={"licoes": ["a-criacao", "o-ceu"]}, headers=ANA
    ).json()
    assert profile["pontos"] == 20
    assert profile["licoes"] == ["a-criacao", "o-ceu"]


def test_should_rank_only_who_opted_in_and_without_private_data(client: TestClient) -> None:
    for headers, name, opted_in in [(ANA, "Ana", True), (BIA, "Bia", False)]:
        client.post("/api/perfil", json={"nome": name}, headers=headers)
        client.put(
            "/api/perfil",
            json={"nome": name, "preferencias": [], "no_ranking": opted_in},
            headers=headers,
        )
        client.post("/api/perfil/licoes", json={"licoes": ["a-criacao"]}, headers=headers)

    assert client.get("/api/ranking").json() == [{"nome": "Ana", "pontos": 10}]


def test_should_delete_the_profile_and_its_progress(client: TestClient) -> None:
    client.post("/api/perfil", json={"nome": "Ana"}, headers=ANA)
    client.post("/api/perfil/licoes", json={"licoes": ["a-criacao"]}, headers=ANA)
    assert client.delete("/api/perfil", headers=ANA).status_code == 204
    assert client.post("/api/perfil", json={"nome": "Ana"}, headers=ANA).json()["pontos"] == 0
