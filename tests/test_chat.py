"""Testes do chatbot (`POST /api/chat`): 503 sem configuração, rate limit,
recusa quando nada bate no acervo, e resposta com fontes quando bate.

`embed_query`/`generate_answer` são sempre mockados — nenhum teste chama
Voyage ou Claude de verdade (sem chave, sem custo, sem rede)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

import app.chat_router as chat_router_module
from app.main import app
from app.rag.chunking import ChunkInput
from app.rag.repository import InMemoryRagRepository


@pytest.fixture()
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def reset_rate_limiter() -> Iterator[None]:
    chat_router_module._rate_limiter._last_seen.clear()
    yield
    chat_router_module._rate_limiter._last_seen.clear()


def test_should_return_503_when_chatbot_not_configured(client: TestClient) -> None:
    # Given
    client.app.state.rag_repository = None

    # When
    response = client.post("/api/chat", json={"pergunta": "O que é a Crisma?"})

    # Then
    assert response.status_code == 503
    assert response.json()["code"] == "CHAT_INDISPONIVEL"


def test_should_reject_empty_question(client: TestClient) -> None:
    # Given
    client.app.state.rag_repository = InMemoryRagRepository()

    # When
    response = client.post("/api/chat", json={"pergunta": ""})

    # Then
    assert response.status_code == 422


def test_should_reject_question_over_max_length(client: TestClient) -> None:
    # Given
    client.app.state.rag_repository = InMemoryRagRepository()

    # When
    response = client.post("/api/chat", json={"pergunta": "a" * 501})

    # Then
    assert response.status_code == 422


async def _fake_embed_query(pergunta: str) -> list[float]:
    return [1.0, 0.0, 0.0]


def test_should_refuse_when_nothing_in_the_index_is_relevant(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Índice vazio → recusa, sem fontes na resposta.

    `generate_answer` real roda aqui (não mockado): com trechos vazios ela
    mesma recusa sem tocar rede nem exigir `ANTHROPIC_API_KEY` (ver
    `tests/test_rag_generation.py` pra essa garantia isolada) — então
    exercitar o fluxo completo até `chat()` continua seguro em CI."""
    # Given
    client.app.state.rag_repository = InMemoryRagRepository()
    monkeypatch.setattr(chat_router_module, "embed_query", _fake_embed_query)

    # When
    response = client.post("/api/chat", json={"pergunta": "Qual a capital da França?"})

    # Then
    assert response.status_code == 200
    body = response.json()
    assert body["fontes"] == []
    assert "não encontrei" in body["resposta"].lower()


def test_should_answer_with_sources_when_a_relevant_chunk_exists(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given
    repo = InMemoryRagRepository()

    async def _seed() -> None:
        chunk = ChunkInput(
            fonte_tipo="acervo",
            fonte_ref="santos/francisco-de-assis",
            titulo="São Francisco de Assis",
            texto="Fundador da Ordem dos Frades Menores.",
        )
        await repo.replace_source("acervo", "santos/francisco-de-assis", [chunk], [[1.0, 0.0, 0.0]])

    import asyncio

    asyncio.run(_seed())
    client.app.state.rag_repository = repo

    monkeypatch.setattr(chat_router_module, "embed_query", _fake_embed_query)

    async def _fake_generate(pergunta: str, trechos: list) -> str:
        assert len(trechos) == 1
        return "São Francisco de Assis fundou a Ordem dos Frades Menores."

    monkeypatch.setattr(chat_router_module, "generate_answer", _fake_generate)

    # When
    response = client.post("/api/chat", json={"pergunta": "Quem fundou os franciscanos?"})

    # Then
    assert response.status_code == 200
    body = response.json()
    assert "Frades Menores" in body["resposta"]
    assert body["fontes"] == [
        {"titulo": "São Francisco de Assis", "categoria": "santos", "slug": "francisco-de-assis"}
    ]


def test_should_rate_limit_rapid_consecutive_questions(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given
    client.app.state.rag_repository = InMemoryRagRepository()
    monkeypatch.setattr(chat_router_module, "embed_query", _fake_embed_query)

    async def _fake_generate(pergunta: str, trechos: list) -> str:
        return "resposta"

    monkeypatch.setattr(chat_router_module, "generate_answer", _fake_generate)

    # When
    first = client.post("/api/chat", json={"pergunta": "Primeira pergunta?"})
    second = client.post("/api/chat", json={"pergunta": "Segunda pergunta logo em seguida?"})

    # Then
    assert first.status_code == 200
    assert second.status_code == 429
