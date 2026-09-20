"""Testes de integração das rotas do acervo (pt-BR) via TestClient (app
real, dados reais)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import Category


@pytest.fixture(scope="module")
def client() -> TestClient:
    """TestClient com lifespan ativo — garante que o acervo foi carregado."""
    with TestClient(app) as test_client:
        yield test_client


def test_should_report_ok_when_health_is_called(client: TestClient) -> None:
    """Health confirma que o acervo está em memória, não só que o processo subiu."""
    # Given / When
    response = client.get("/api/health")

    # Then
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["categorias"] == len(Category)
    assert body["total_entradas"] > 0


def test_should_list_categories_with_totals_when_requested(
    client: TestClient,
) -> None:
    """A home do frontend consome categorias já com o total de entradas."""
    # Given / When
    response = client.get("/api/categories")

    # Then
    assert response.status_code == 200
    body = response.json()
    assert len(body) == len(Category)
    assert all(item["total"] > 0 for item in body)


def test_should_return_paginated_entries_when_listing_a_category(
    client: TestClient,
) -> None:
    """Listagem devolve metadados de paginação junto com os itens."""
    # Given / When
    response = client.get("/api/santos", params={"limit": 2, "offset": 0})

    # Then
    assert response.status_code == 200
    body = response.json()
    assert body["categoria"] == "santos"
    assert body["limit"] == 2
    assert len(body["itens"]) <= 2
    assert body["total"] >= len(body["itens"])


def test_should_return_404_when_category_does_not_exist(client: TestClient) -> None:
    """Categoria inexistente é recurso inexistente: 404 com código estável."""
    # Given / When
    response = client.get("/api/rezas-inventadas")

    # Then
    assert response.status_code == 404
    assert response.json()["code"] == "CATEGORY_NOT_FOUND"


def test_should_return_entry_detail_when_slug_exists(client: TestClient) -> None:
    """Detalhe traz corpo, fontes e os campos próprios da categoria."""
    # Given / When
    response = client.get("/api/papas/joao-paulo-ii")

    # Then
    assert response.status_code == 200
    body = response.json()
    assert body["slug"] == "joao-paulo-ii"
    assert body["numero_ordem"] == 264
    assert body["fontes"]


def test_should_return_404_when_slug_does_not_exist(client: TestClient) -> None:
    """Slug inexistente devolve 404 com o código ENTRY_NOT_FOUND."""
    # Given / When
    response = client.get("/api/papas/papa-inexistente")

    # Then
    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "ENTRY_NOT_FOUND"
    assert body["message"]


def test_should_search_across_categories_when_no_filter_is_given(
    client: TestClient,
) -> None:
    """Busca global devolve categoria, slug, título e trecho de contexto."""
    # Given / When
    response = client.get("/api/search", params={"q": "eucaristia", "limit": 5})

    # Then
    assert response.status_code == 200
    results = response.json()
    assert results
    assert len(results) <= 5
    assert set(results[0]) == {"categoria", "slug", "titulo", "trecho"}


def test_should_filter_search_when_category_is_given(client: TestClient) -> None:
    """O filtro de categoria da busca é aplicado no servidor."""
    # Given / When
    response = client.get(
        "/api/search", params={"q": "teresa", "categoria": "santos"}
    )

    # Then
    assert response.status_code == 200
    results = response.json()
    assert results
    assert all(item["categoria"] == "santos" for item in results)


def test_should_return_404_when_search_category_is_unknown(
    client: TestClient,
) -> None:
    """Filtro com categoria inexistente falha explicitamente, não silenciosamente."""
    # Given / When
    response = client.get("/api/search", params={"q": "fe", "categoria": "nada"})

    # Then
    assert response.status_code == 404
    assert response.json()["code"] == "CATEGORY_NOT_FOUND"


def test_should_reject_search_when_query_is_too_short(client: TestClient) -> None:
    """Busca de 1 caractere varreria o acervo inteiro sem serventia: 422."""
    # Given / When
    response = client.get("/api/search", params={"q": "a"})

    # Then
    assert response.status_code == 422


def test_should_allow_frontend_origin_when_cors_preflight_is_sent(
    client: TestClient,
) -> None:
    """O frontend em localhost:3000 precisa passar no preflight."""
    # Given / When
    response = client.options(
        "/api/categories",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    # Then
    assert response.status_code == 200
    assert (
        response.headers["access-control-allow-origin"] == "http://localhost:3000"
    )


def test_should_not_collide_i18n_route_with_portuguese_entry_detail(
    client: TestClient,
) -> None:
    """`/api/{categoria}/{slug}` (detalhe em português) e
    `/api/i18n/{lang}/{categoria}` (lista traduzida) têm o mesmo formato
    `/api/X/Y` — o prefixo fixo `i18n` entre eles é o que evita colisão."""
    # Given / When
    response = client.get("/api/santos/francisco-de-assis")

    # Then
    assert response.status_code == 200
    assert response.json()["categoria"] == "santos"
