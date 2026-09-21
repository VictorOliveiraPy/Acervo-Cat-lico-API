"""Testes do chatbot (`POST /api/chat`): 503 sem configuração, validação,
rate limit, recusa quando nada bate no acervo, e resposta com fontes
quando bate. Nenhum teste chama Voyage ou DeepSeek de verdade — os gateways
reais nunca são usados, só fakes injetados em `app.state`."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.domain.chat.entities import ChunkInput, ChunkResult
from app.infrastructure.chat.in_memory_repository import InMemoryRagRepository
from app.interface.chat.router import _rate_limiter
from app.main import app


class _FakeEmbeddingGateway:
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0, 0.0] for _ in texts]

    async def embed_query(self, question: str) -> list[float]:
        return [1.0, 0.0, 0.0]


class _FakeAnswerGenerator:
    def __init__(self, answer: str = "resposta") -> None:
        self._answer = answer
        self.chunks_received: list[ChunkResult] = []

    async def generate(self, question: str, chunks: list[ChunkResult]) -> str:
        self.chunks_received = chunks
        return self._answer


@pytest.fixture()
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def reset_rate_limiter() -> Iterator[None]:
    _rate_limiter._last_seen.clear()
    yield
    _rate_limiter._last_seen.clear()


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


def test_should_refuse_when_nothing_in_the_index_is_relevant(client: TestClient) -> None:
    # Given — índice vazio, nenhum trecho bate
    client.app.state.rag_repository = InMemoryRagRepository()
    client.app.state.embedding_gateway = _FakeEmbeddingGateway()
    client.app.state.answer_generator = _FakeAnswerGenerator()

    # When
    response = client.post("/api/chat", json={"pergunta": "Qual a capital da França?"})

    # Then
    assert response.status_code == 200
    body = response.json()
    assert body["fontes"] == []
    assert "não encontrei" in body["resposta"].lower()


def test_should_answer_with_sources_when_a_relevant_chunk_exists(client: TestClient) -> None:
    # Given
    repo = InMemoryRagRepository()
    import asyncio

    async def _seed() -> None:
        chunk = ChunkInput(
            source_type="acervo",
            source_ref="santos/francisco-de-assis",
            title="São Francisco de Assis",
            text="Fundador da Ordem dos Frades Menores.",
        )
        await repo.replace_source("acervo", "santos/francisco-de-assis", [chunk], [[1.0, 0.0, 0.0]])

    asyncio.run(_seed())
    client.app.state.rag_repository = repo
    client.app.state.embedding_gateway = _FakeEmbeddingGateway()
    client.app.state.answer_generator = _FakeAnswerGenerator(
        answer="São Francisco de Assis fundou a Ordem dos Frades Menores."
    )

    # When
    response = client.post("/api/chat", json={"pergunta": "Quem fundou os franciscanos?"})

    # Then
    assert response.status_code == 200
    body = response.json()
    assert "Frades Menores" in body["resposta"]
    assert body["fontes"] == [
        {"titulo": "São Francisco de Assis", "categoria": "santos", "slug": "francisco-de-assis"}
    ]


def test_should_rate_limit_rapid_consecutive_questions(client: TestClient) -> None:
    # Given
    client.app.state.rag_repository = InMemoryRagRepository()
    client.app.state.embedding_gateway = _FakeEmbeddingGateway()
    client.app.state.answer_generator = _FakeAnswerGenerator()

    # When
    first = client.post("/api/chat", json={"pergunta": "Primeira pergunta?"})
    second = client.post("/api/chat", json={"pergunta": "Segunda pergunta logo em seguida?"})

    # Then
    assert first.status_code == 200
    assert second.status_code == 429
