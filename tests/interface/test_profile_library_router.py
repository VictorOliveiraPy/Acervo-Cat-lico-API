"""Padroeiro, favoritos e anotações: autorização, validação e isolamento entre pessoas."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.domain.profiles import entities
from app.infrastructure.profiles import in_memory_repository
from app.infrastructure.profiles.in_memory_repository import InMemoryProfileRepository
from app.interface.profiles.router import _write_limiter, get_profile_repository
from app.main import app

SECRET = "segredo-de-teste"
ANA = {"X-Internal-Secret": SECRET, "X-User-Sub": "google-ana"}
BIA = {"X-Internal-Secret": SECRET, "X-User-Sub": "google-bia"}
FAVORITE = {"tipo": "Bíblia", "texto": "O Senhor é meu pastor.", "referencia": "Sl 23,1"}
NOTE = {"categoria": "Lição", "texto": "Revisar a Trindade.", "licao": "santissima-trindade"}
ROUTES = [("/api/perfil/favoritos", FAVORITE), ("/api/perfil/anotacoes", NOTE)]


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setattr(settings, "internal_api_secret", SECRET)
    monkeypatch.setattr(_write_limiter, "_enabled", False)
    repo = InMemoryProfileRepository()
    app.dependency_overrides[get_profile_repository] = lambda: repo
    test_client = TestClient(app)
    for headers, nome in [(ANA, "Ana"), (BIA, "Bia")]:
        test_client.post("/api/perfil", json={"nome": nome}, headers=headers)
    yield test_client
    app.dependency_overrides.pop(get_profile_repository, None)
    _write_limiter._last_seen.clear()


@pytest.mark.parametrize(("path", "body"), ROUTES)
def test_should_refuse_without_the_shared_secret(
    client: TestClient, path: str, body: dict[str, str]
) -> None:
    without_secret = {"X-User-Sub": "google-ana"}
    assert client.get(path, headers=without_secret).status_code == 401
    assert client.post(path, json=body, headers=without_secret).status_code == 401
    assert client.delete(f"{path}/1", headers=without_secret).status_code == 401


@pytest.mark.parametrize(("path", "body"), ROUTES)
def test_should_not_let_one_person_see_or_delete_another_persons_items(
    client: TestClient, path: str, body: dict[str, str]
) -> None:
    item_id = client.post(path, json=body, headers=ANA).json()["id"]

    assert client.get(path, headers=BIA).json() == []
    assert client.delete(f"{path}/{item_id}", headers=BIA).status_code == 404
    assert [item["id"] for item in client.get(path, headers=ANA).json()] == [item_id]


@pytest.mark.parametrize(("path", "body"), ROUTES)
def test_should_list_newest_first_and_delete(
    client: TestClient, path: str, body: dict[str, str]
) -> None:
    first = client.post(path, json=body, headers=ANA).json()["id"]
    second = client.post(path, json=body, headers=ANA).json()["id"]

    assert [item["id"] for item in client.get(path, headers=ANA).json()] == [second, first]
    assert client.delete(f"{path}/{first}", headers=ANA).status_code == 204
    assert client.delete(f"{path}/{first}", headers=ANA).status_code == 404
    assert [item["id"] for item in client.get(path, headers=ANA).json()] == [second]


@pytest.mark.parametrize(("path", "body"), ROUTES)
def test_should_accept_2000_characters_and_refuse_more(
    client: TestClient, path: str, body: dict[str, str]
) -> None:
    assert client.post(path, json={**body, "texto": "a" * 2000}, headers=ANA).status_code == 201
    assert client.post(path, json={**body, "texto": "a" * 2001}, headers=ANA).status_code == 422
    assert client.post(path, json={**body, "texto": "   "}, headers=ANA).status_code == 422


@pytest.mark.parametrize(("path", "body"), ROUTES)
def test_should_not_echo_the_refused_text_in_the_error(
    client: TestClient, path: str, body: dict[str, str]
) -> None:
    secret_text = "segredo " * 300
    response = client.post(path, json={**body, "texto": secret_text}, headers=ANA)
    assert response.status_code == 422
    assert "segredo" not in response.text


@pytest.mark.parametrize(
    ("path", "body"),
    [
        ("/api/perfil/favoritos", {**FAVORITE, "tipo": "Outro"}),
        ("/api/perfil/anotacoes", {**NOTE, "categoria": "Outra"}),
    ],
)
def test_should_refuse_unknown_kinds(client: TestClient, path: str, body: dict[str, str]) -> None:
    assert client.post(path, json=body, headers=ANA).status_code == 422


@pytest.mark.parametrize(
    "url",
    ["javascript:alert(1)", "https://exemplo.com", "//exemplo.com", "/\\exemplo.com", "/a b"],
)
def test_should_accept_only_site_paths_as_source(client: TestClient, url: str) -> None:
    response = client.post(
        "/api/perfil/favoritos", json={**FAVORITE, "url_origem": url}, headers=ANA
    )
    assert response.status_code == 422


def test_should_keep_the_source_path(client: TestClient) -> None:
    body = {**FAVORITE, "url_origem": "/santos/francisco-de-assis"}
    created = client.post("/api/perfil/favoritos", json=body, headers=ANA).json()
    assert created["url_origem"] == "/santos/francisco-de-assis"


@pytest.mark.parametrize(("path", "body"), ROUTES)
def test_should_stop_at_the_limit_per_person(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, path: str, body: dict[str, str]
) -> None:
    monkeypatch.setattr(in_memory_repository, "MAX_ITEMS_PER_USER", 1)
    assert client.post(path, json=body, headers=ANA).status_code == 201

    refused = client.post(path, json=body, headers=ANA)

    assert refused.status_code == 409
    assert refused.json()["code"] == "LIMITE_ATINGIDO"
    assert client.post(path, json=body, headers=BIA).status_code == 201


def test_should_have_the_agreed_limit_per_person() -> None:
    assert entities.MAX_ITEMS_PER_USER == 500


@pytest.mark.parametrize(("path", "body"), ROUTES)
def test_should_answer_404_when_the_profile_does_not_exist(
    client: TestClient, path: str, body: dict[str, str]
) -> None:
    stranger = {"X-Internal-Secret": SECRET, "X-User-Sub": "google-sem-perfil"}
    assert client.post(path, json=body, headers=stranger).status_code == 404


def test_should_limit_writes_per_person_and_not_per_server(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(_write_limiter, "_enabled", True)
    path, body = ROUTES[0]
    assert client.post(path, json=body, headers=ANA).status_code == 201
    assert client.post(path, json=body, headers=ANA).status_code == 429
    # Mesmo IP de origem (o servidor do site), outra pessoa: não pode ser bloqueada.
    assert client.post(path, json=body, headers=BIA).status_code == 201


def test_should_delete_favorites_and_notes_with_the_account(client: TestClient) -> None:
    for path, body in ROUTES:
        client.post(path, json=body, headers=ANA)

    assert client.delete("/api/perfil", headers=ANA).status_code == 204
    client.post("/api/perfil", json={"nome": "Ana"}, headers=ANA)

    for path, _ in ROUTES:
        assert client.get(path, headers=ANA).json() == []


def test_should_default_and_change_the_patron(client: TestClient) -> None:
    profile = client.post("/api/perfil", json={"nome": "Ana"}, headers=ANA).json()
    assert profile["padroeiro_id"] == "francisco"

    changed = client.put("/api/perfil/padroeiro", json={"padroeiro_id": "jose"}, headers=ANA)

    assert changed.json()["padroeiro_id"] == "jose"
    assert client.post("/api/perfil", json={"nome": "Bia"}, headers=BIA).json()[
        "padroeiro_id"
    ] == "francisco"


def test_should_refuse_an_unknown_patron(client: TestClient) -> None:
    response = client.put("/api/perfil/padroeiro", json={"padroeiro_id": "x"}, headers=ANA)
    assert response.status_code == 422
