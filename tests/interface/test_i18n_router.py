"""Testes de integração das rotas de tradução (`/api/i18n/{lang}/...`) via
TestClient (app real, dados reais)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    """TestClient com lifespan ativo — garante que as traduções foram carregadas."""
    with TestClient(app) as test_client:
        yield test_client


def test_should_404_when_i18n_language_is_not_supported(client: TestClient) -> None:
    """Idioma fora de `SUPPORTED_LANGUAGES`
    (`app.infrastructure.acervo.translations`): 404 dedicado, não confuso
    com categoria inexistente."""
    # Given / When
    response = client.get("/api/i18n/fr/categories")

    # Then
    assert response.status_code == 404
    assert response.json()["code"] == "LANGUAGE_NOT_FOUND"


def test_should_list_only_translated_categories_for_i18n_language(
    client: TestClient,
) -> None:
    """`/api/i18n/es/categories` nunca quebra mesmo sem nenhuma tradução
    ainda — lista vazia é estado válido (tradução incremental)."""
    # Given / When
    response = client.get("/api/i18n/es/categories")

    # Then
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_should_404_when_i18n_category_not_translated_yet(client: TestClient) -> None:
    """Categoria válida no enum, mas sem tradução pra este idioma: 404 igual
    a uma categoria que não existe — nunca um erro cru de servidor."""
    # Given / When
    response = client.get("/api/i18n/es/santos")

    # Then
    assert response.status_code == 404
    assert response.json()["code"] == "CATEGORY_NOT_FOUND"
