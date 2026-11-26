"""Rotas do perfil e do ranking, com repositório em memória."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.infrastructure.profiles.in_memory_repository import InMemoryProfileRepository
from app.interface.profiles.router import brazil_today, get_profile_repository
from app.main import app

SECRET = "segredo-de-teste"
ANA = {"X-Internal-Secret": SECRET, "X-User-Sub": "google-ana"}
BIA = {"X-Internal-Secret": SECRET, "X-User-Sub": "google-bia"}
DAY = date(2026, 11, 15)


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setattr(settings, "internal_api_secret", SECRET)
    repo = InMemoryProfileRepository()
    app.dependency_overrides[get_profile_repository] = lambda: repo
    app.dependency_overrides[brazil_today] = lambda: DAY
    yield TestClient(app)
    app.dependency_overrides.pop(get_profile_repository, None)
    app.dependency_overrides.pop(brazil_today, None)


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


def _done_today(profile: dict[str, object]) -> list[str]:
    return [a["id"] for a in profile["atividades"] if a["feita_hoje"]]  # type: ignore[attr-defined,index]


def test_should_list_the_activities_with_their_points(client: TestClient) -> None:
    profile = client.post("/api/perfil", json={"nome": "Ana"}, headers=ANA).json()
    terco = next(a for a in profile["atividades"] if a["id"] == "terco")
    assert terco == {
        "id": "terco",
        "nome": "Rezar o Terço",
        "descricao": "Complete as 5 dezenas do terço",
        "pontos": 15,
        "pontos_hoje": 15,
        "feita_hoje": False,
    }
    assert len(profile["atividades"]) == 9


def test_should_score_an_activity_once_per_day(client: TestClient) -> None:
    client.post("/api/perfil", json={"nome": "Ana"}, headers=ANA)
    client.post("/api/perfil/licoes", json={"licoes": ["a-criacao"]}, headers=ANA)

    first = client.post("/api/perfil/atividades", json={"atividade": "missa"}, headers=ANA)
    again = client.post("/api/perfil/atividades", json={"atividade": "missa"}, headers=ANA)

    assert first.json()["pontos"] == 10 + 50
    assert again.json()["pontos"] == 10 + 50
    assert _done_today(again.json()) == ["missa"]


def test_should_score_again_on_the_next_day(client: TestClient) -> None:
    client.post("/api/perfil", json={"nome": "Ana"}, headers=ANA)
    client.post("/api/perfil/atividades", json={"atividade": "terco"}, headers=ANA)

    app.dependency_overrides[brazil_today] = lambda: date(2026, 11, 16)
    next_day = client.post("/api/perfil", json={"nome": "Ana"}, headers=ANA).json()
    assert next_day["pontos"] == 15
    assert _done_today(next_day) == []

    done = client.post("/api/perfil/atividades", json={"atividade": "terco"}, headers=ANA)
    assert done.json()["pontos"] == 30


def test_should_refuse_an_unknown_activity(client: TestClient) -> None:
    client.post("/api/perfil", json={"nome": "Ana"}, headers=ANA)
    response = client.post("/api/perfil/atividades", json={"atividade": "x"}, headers=ANA)
    assert response.status_code == 422


def test_should_rank_activity_points(client: TestClient) -> None:
    client.post("/api/perfil", json={"nome": "Ana"}, headers=ANA)
    client.put(
        "/api/perfil",
        json={"nome": "Ana", "preferencias": [], "no_ranking": True},
        headers=ANA,
    )
    client.post("/api/perfil/atividades", json={"atividade": "caridade"}, headers=ANA)

    assert client.get("/api/ranking").json() == [{"nome": "Ana", "pontos": 40}]


def _on(day: date) -> None:
    app.dependency_overrides[brazil_today] = lambda: day


def test_should_start_at_level_one_without_a_streak(client: TestClient) -> None:
    profile = client.post("/api/perfil", json={"nome": "Ana"}, headers=ANA).json()
    assert profile["nivel"] == {
        "numero": 1,
        "titulo": "Peregrino Iniciante",
        "estagio": 1,
        "xp_no_nivel": 0,
        "xp_proximo_nivel": 114,
    }
    assert profile["sequencia"] == {"atual": 0, "recorde": 0, "multiplicador": 1.0}


def test_should_level_up_from_the_points(client: TestClient) -> None:
    client.post("/api/perfil", json={"nome": "Ana"}, headers=ANA)
    lessons = [f"licao-{n}" for n in range(12)]
    profile = client.post("/api/perfil/licoes", json={"licoes": lessons}, headers=ANA).json()
    assert profile["pontos"] == 120
    assert profile["nivel"]["numero"] == 2
    assert profile["nivel"]["xp_no_nivel"] == 6
    assert profile["nivel"]["xp_proximo_nivel"] == 132


def test_should_keep_the_streak_with_a_lesson_or_a_practice(client: TestClient) -> None:
    client.post("/api/perfil", json={"nome": "Ana"}, headers=ANA)
    client.post("/api/perfil/licoes", json={"licoes": ["a-criacao"]}, headers=ANA)
    _on(date(2026, 11, 16))
    profile = client.post(
        "/api/perfil/atividades", json={"atividade": "terco"}, headers=ANA
    ).json()
    assert profile["sequencia"]["atual"] == 2


def test_should_reset_the_streak_after_a_missed_day_but_keep_the_record(
    client: TestClient,
) -> None:
    client.post("/api/perfil", json={"nome": "Ana"}, headers=ANA)
    for day in (15, 16, 18):
        _on(date(2026, 11, day))
        profile = client.post(
            "/api/perfil/atividades", json={"atividade": "terco"}, headers=ANA
        ).json()
    assert profile["sequencia"] == {"atual": 1, "recorde": 2, "multiplicador": 1.0}


def test_should_multiply_practice_points_from_the_seventh_day(client: TestClient) -> None:
    client.post("/api/perfil", json={"nome": "Ana"}, headers=ANA)
    for day in range(15, 21):  # 6 dias seguidos, sem bônus
        _on(date(2026, 11, day))
        client.post("/api/perfil/atividades", json={"atividade": "terco"}, headers=ANA)

    _on(date(2026, 11, 21))
    before = client.post("/api/perfil", json={"nome": "Ana"}, headers=ANA).json()
    # Ontem ativo: marcar hoje faz o sétimo dia, então o bônus já vale hoje.
    assert before["sequencia"]["atual"] == 6
    assert before["sequencia"]["multiplicador"] == 1.5
    terco = next(a for a in before["atividades"] if a["id"] == "terco")
    assert terco["pontos_hoje"] == 22

    after = client.post(
        "/api/perfil/atividades", json={"atividade": "terco"}, headers=ANA
    ).json()
    assert after["pontos"] == 6 * 15 + 22
    assert after["sequencia"]["atual"] == 7


def test_path_definition_is_public(client: TestClient) -> None:
    body = client.get("/api/caminho").json()
    assert [via["id"] for via in body["vias"]] == ["purgativa", "iluminativa", "unitiva"]
    assert len(body["casas"]) == 36
    first = body["casas"][0]
    assert set(first) == {"numero", "via", "titulo", "texto", "tipo", "tarefa", "tarefa_nome", "licoes"}
    assert first["numero"] == 1 and first["tipo"] == "atividade"


def test_path_advances_one_house_per_task(client: TestClient) -> None:
    profile = client.post("/api/perfil", json={"nome": "Ana"}, headers=ANA).json()
    assert profile["caminho"] == {"concluidas": 0, "hoje": []}
    first = client.get("/api/caminho").json()["casas"][0]

    refused = client.post("/api/perfil/caminho", json={"casa": 1}, headers=ANA)
    assert refused.status_code == 409 and refused.json()["code"] == "CAMINHO_BLOQUEADO"
    assert "Marque" in refused.json()["message"]

    client.post("/api/perfil/atividades", json={"atividade": first["tarefa"]}, headers=ANA)
    done = client.post("/api/perfil/caminho", json={"casa": 1}, headers=ANA)
    assert done.status_code == 200 and done.json()["caminho"] == {"concluidas": 1, "hoje": [1]}
    # Pular casa não vale; a mesma casa de novo também não.
    assert client.post("/api/perfil/caminho", json={"casa": 3}, headers=ANA).status_code == 409
    assert client.post("/api/perfil/caminho", json={"casa": 1}, headers=ANA).status_code == 409
    assert client.post("/api/perfil/caminho", json={"casa": 99}, headers=ANA).status_code == 422


def test_path_needs_a_profile_and_the_secret(client: TestClient) -> None:
    assert client.post("/api/perfil/caminho", json={"casa": 1}, headers={"X-User-Sub": "x"}).status_code == 401
    assert client.post("/api/perfil/caminho", json={"casa": 1}, headers=BIA).status_code == 404
