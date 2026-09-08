"""Testes da liturgia diária: parsing do payload externo, cache e 503 sem
banco configurado. Nenhum teste toca a rede — `fetch_liturgia` de verdade
nunca é chamado, só `parse_liturgia` (função pura) e fakes injetados."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.liturgia_client import parse_liturgia
from app.liturgia_models import LiturgiaDiaria
from app.liturgia_repository import InMemoryLiturgiaDiariaRepository
from app.main import app

# Trecho real da resposta da fonte externa para um dia de semana (sem
# segunda leitura), aparado para o que o parser lê.
PAYLOAD_DIA_DE_SEMANA = {
    "today": {
        "color": "branco",
        "entry_title": "<b>Tempo:</b> Comum<br/><b>Festa:</b> Natividade de Nossa Senhora",
        "readings": {
            "first_reading": {
                "title": "Primeira leitura: Miqueias 5, 1-4",
                "head": "Leitura da Profecia de Miquéias:",
                "text": "Assim diz o Senhor: 1Tu, Belém de Éfrata... [texto]",
                "footer": "- Palavra do Senhor",
                "footer_response": "- Graças a Deus",
            },
            "psalm": {
                "title": "Salmo 70 (71); 12 (13)",
                "response": "R: Exulto de alegria no Senhor.",
                "content_psalm": [
                    "- Sois meu apoio desde antes que eu nascesse...",
                    "- Uma vez que confiei no vosso amor...",
                ],
            },
            "gospel": {
                "title": "Proclamação do Evangelho de Jesus Cristo segundo São Mateus:",
                "head_title": "Evangelho de Jesus Cristo segundo São Mateus 1, 1-16.18-23",
                "head": "- Sois feliz, Virgem Maria...",
                "head_response": "- Aleluia, Aleluia, Aleluia.",
                "text": "A origem de Jesus Cristo foi assim... [texto]",
                "footer": "- Palavra da Salvação",
                "footer_response": "- Glória a Vós, Senhor",
            },
        },
    }
}

# Mesma forma, mas com segunda leitura (domingo/solenidade).
PAYLOAD_DOMINGO = {
    "today": {
        "color": "verde",
        "entry_title": "24o. Domingo do Tempo Comum",
        "readings": {
            "first_reading": {
                "title": "Primeira leitura: Isaías 50, 5-9a",
                "text": "texto da primeira leitura",
            },
            "psalm": {
                "title": "Salmo 114 (116)",
                "response": "R: Andarei na presença do Senhor.",
                "content_psalm": ["linha 1", "linha 2"],
            },
            "second_reading": {
                "title": "Segunda leitura: Romanos 14, 7-9",
                "head": "Leitura da Carta de São Paulo aos Romanos:",
                "text": "texto da segunda leitura",
            },
            "gospel": {
                "title": "Proclamação do Evangelho...",
                "head_title": "Evangelho de Jesus Cristo segundo São Marcos 8, 27-35",
                "text": "texto do evangelho",
            },
        },
    }
}


def test_should_parse_weekday_payload_without_second_reading() -> None:
    # When
    liturgia = parse_liturgia(date(2026, 9, 8), PAYLOAD_DIA_DE_SEMANA)

    # Then
    assert liturgia.data == date(2026, 9, 8)
    assert liturgia.cor_liturgica == "branco"
    assert liturgia.celebracao == "Tempo: Comum Festa: Natividade de Nossa Senhora"
    assert liturgia.primeira_leitura.referencia == "Primeira leitura: Miqueias 5, 1-4"
    assert "Belém" in liturgia.primeira_leitura.texto
    assert liturgia.salmo.referencia == "Salmo 70 (71); 12 (13)"
    assert "Exulto de alegria" in liturgia.salmo.texto
    assert liturgia.segunda_leitura is None
    assert liturgia.evangelho.referencia == "Evangelho de Jesus Cristo segundo São Mateus 1, 1-16.18-23"
    assert "origem de Jesus Cristo" in liturgia.evangelho.texto
    assert liturgia.fonte == "sagradaliturgia.com.br"


def test_should_parse_sunday_payload_with_second_reading() -> None:
    # When
    liturgia = parse_liturgia(date(2026, 9, 13), PAYLOAD_DOMINGO)

    # Then
    assert liturgia.segunda_leitura is not None
    assert liturgia.segunda_leitura.referencia == "Segunda leitura: Romanos 14, 7-9"
    assert liturgia.segunda_leitura.texto == "texto da segunda leitura"
    assert liturgia.evangelho.referencia == "Evangelho de Jesus Cristo segundo São Marcos 8, 27-35"


def test_parse_should_strip_html_tags_from_celebracao() -> None:
    # When
    liturgia = parse_liturgia(date(2026, 9, 8), PAYLOAD_DIA_DE_SEMANA)

    # Then
    assert "<b>" not in (liturgia.celebracao or "")
    assert "<br/>" not in (liturgia.celebracao or "")


@pytest.fixture()
def client() -> Iterator[TestClient]:
    """TestClient próprio (não o `module`-scoped de test_routers): cada
    teste aqui manipula `app.state.liturgia_repository`, então precisa de
    isolamento por teste, não compartilhado."""
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

    client.app.state.liturgia_repository = InMemoryLiturgiaDiariaRepository(fake_fetch)

    # When
    response = client.get("/api/liturgia-diaria", params={"data": "2026-09-08"})

    # Then
    assert response.status_code == 200
    body = response.json()
    assert body["data"] == "2026-09-08"
    assert body["evangelho"]["referencia"] == "Evangelho de Jesus Cristo segundo São Mateus 1, 1-16.18-23"


def test_should_cache_and_call_fetcher_only_once_per_date(client: TestClient) -> None:
    # Given
    chamadas = 0

    async def fake_fetch(dia: date) -> LiturgiaDiaria:
        nonlocal chamadas
        chamadas += 1
        return parse_liturgia(dia, PAYLOAD_DIA_DE_SEMANA)

    client.app.state.liturgia_repository = InMemoryLiturgiaDiariaRepository(fake_fetch)

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

    client.app.state.liturgia_repository = InMemoryLiturgiaDiariaRepository(failing_fetch)

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

    client.app.state.liturgia_repository = InMemoryLiturgiaDiariaRepository(fake_fetch)

    # When
    response = client.get("/api/liturgia-diaria")

    # Then
    assert response.status_code == 200
    assert len(recebido) == 1
    assert recebido[0] == date.fromisoformat(response.json()["data"])
