"""Rotas das métricas: só o servidor do site grava e lê; robô e lixo não contam."""

from __future__ import annotations

import json
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.infrastructure.metrics.in_memory_repository import InMemoryMetricsRepository
from app.interface.metrics.router import _per_minute
from app.main import app

SECRET = "segredo-de-teste"
BROWSER = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36"
)
HEADERS = {
    "X-Internal-Secret": SECRET,
    "X-Visitante-IP": "200.1.2.3",
    "X-Visitante-UA": BROWSER,
}


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setattr(settings, "internal_api_secret", SECRET)
    _per_minute.clear()
    with TestClient(app) as test_client:
        test_client.app.state.metrics_repository = InMemoryMetricsRepository()
        yield test_client


def _post(client: TestClient, payload: object, headers: dict[str, str] = HEADERS):
    # O navegador manda como texto puro (sendBeacon), não como JSON.
    return client.post("/api/metricas", content=json.dumps(payload), headers=headers)


def test_should_record_a_page_view(client: TestClient) -> None:
    response = _post(client, {"tipo": "pagina", "caminho": "/santos?x=1"})
    assert response.status_code == 204
    [hit] = client.app.state.metrics_repository.hits
    assert (hit.path, hit.device) == ("/santos", "computador")


def test_should_refuse_without_the_internal_secret(client: TestClient) -> None:
    response = _post(
        client,
        {"tipo": "pagina", "caminho": "/"},
        {**HEADERS, "X-Internal-Secret": "errado"},
    )
    assert response.status_code == 401
    assert client.app.state.metrics_repository.hits == []


def test_should_ignore_bots_and_garbage_quietly(client: TestClient) -> None:
    assert (
        _post(
            client,
            {"tipo": "pagina", "caminho": "/"},
            {**HEADERS, "X-Visitante-UA": "Googlebot"},
        ).status_code
        == 204
    )
    assert (
        client.post("/api/metricas", content="não é json", headers=HEADERS).status_code
        == 204
    )
    assert (
        _post(
            client, {"tipo": "evento", "caminho": "/", "evento": "inventado"}
        ).status_code
        == 204
    )
    assert client.app.state.metrics_repository.hits == []


def test_should_cap_hits_per_visitor_per_minute(client: TestClient) -> None:
    for _ in range(70):
        _post(client, {"tipo": "pagina", "caminho": "/"})
    assert len(client.app.state.metrics_repository.hits) == 60


def test_should_not_break_the_site_without_database(client: TestClient) -> None:
    client.app.state.metrics_repository = None
    assert _post(client, {"tipo": "pagina", "caminho": "/"}).status_code == 204


def test_summary_needs_the_secret_and_returns_the_period(client: TestClient) -> None:
    _post(
        client,
        {
            "tipo": "pagina",
            "caminho": "/santos",
            "referencia": "https://www.google.com/",
        },
    )
    assert client.get("/api/metricas/resumo").status_code == 401

    response = client.get(
        "/api/metricas/resumo?dias=7", headers={"X-Internal-Secret": SECRET}
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["dias"]) == 7
    assert body["visitantes"] == 1 and body["paginas"] == 1
    assert body["paginas_mais_vistas"] == [{"nome": "/santos", "total": 1}]
    assert body["origens"] == [{"nome": "google.com", "total": 1}]
