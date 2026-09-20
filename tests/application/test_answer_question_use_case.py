"""Testes do use case do chatbot isolados da camada HTTP — nenhum destes
sobe um `TestClient` nem chama Voyage/Claude de verdade, só fakes."""

from __future__ import annotations

import pytest

from app.application.chat.answer_question_use_case import AnswerQuestionUseCase
from app.core.exceptions import ServiceUnavailableException
from app.domain.chat.entities import ChunkInput, ChunkResult, CitedSource
from app.domain.chat.exceptions import AnswerGenerationError, EmbeddingGenerationError
from app.domain.chat.relevance import NO_MATCH_MESSAGE
from app.infrastructure.chat.in_memory_repository import InMemoryRagRepository


class _FakeEmbeddingGateway:
    def __init__(self, vector: list[float] | None = None, should_fail: bool = False) -> None:
        self._vector = vector or [1.0, 0.0, 0.0]
        self._should_fail = should_fail

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector for _ in texts]

    async def embed_query(self, question: str) -> list[float]:
        if self._should_fail:
            raise EmbeddingGenerationError()
        return self._vector


class _FakeAnswerGenerator:
    def __init__(self, answer: str = "resposta", should_fail: bool = False) -> None:
        self._answer = answer
        self._should_fail = should_fail
        self.calls = 0

    async def generate(self, question: str, chunks: list[ChunkResult]) -> str:
        self.calls += 1
        if self._should_fail:
            raise AnswerGenerationError()
        return self._answer


async def test_should_refuse_without_calling_generator_when_nothing_relevant() -> None:
    # Given — índice vazio, nenhum trecho bate
    repo = InMemoryRagRepository()
    generator = _FakeAnswerGenerator()
    use_case = AnswerQuestionUseCase(repo, _FakeEmbeddingGateway(), generator)

    # When
    result = await use_case.execute("Qual a capital da França?")

    # Then
    assert result.answer == NO_MATCH_MESSAGE
    assert result.sources == []
    assert generator.calls == 0


async def test_should_answer_with_sources_when_a_relevant_chunk_exists() -> None:
    # Given
    repo = InMemoryRagRepository()
    await repo.replace_source(
        "acervo",
        "santos/francisco-de-assis",
        [
            ChunkInput(
                source_type="acervo",
                source_ref="santos/francisco-de-assis",
                title="São Francisco de Assis",
                text="Fundador da Ordem dos Frades Menores.",
            )
        ],
        [[1.0, 0.0, 0.0]],
    )
    generator = _FakeAnswerGenerator(answer="São Francisco fundou os franciscanos.")
    use_case = AnswerQuestionUseCase(repo, _FakeEmbeddingGateway(), generator)

    # When
    result = await use_case.execute("Quem fundou os franciscanos?")

    # Then
    assert "franciscanos" in result.answer
    assert generator.calls == 1
    assert result.sources == [
        CitedSource(
            title="São Francisco de Assis", category="santos", slug="francisco-de-assis"
        )
    ]


async def test_should_propagate_embedding_generation_error_without_wrapping() -> None:
    """O use case não tem `try/except` — quem traduz falha de rede/SDK em
    exceção de domínio é o gateway (ver `VoyageEmbeddingGateway`)."""
    # Given
    repo = InMemoryRagRepository()
    use_case = AnswerQuestionUseCase(
        repo, _FakeEmbeddingGateway(should_fail=True), _FakeAnswerGenerator()
    )

    # When / Then
    with pytest.raises(EmbeddingGenerationError) as exc_info:
        await use_case.execute("Qualquer pergunta")
    assert exc_info.value.code == "CHAT_INDISPONIVEL"


async def test_should_propagate_answer_generation_error_without_wrapping() -> None:
    # Given — trecho relevante existe, mas o gerador falha
    repo = InMemoryRagRepository()
    await repo.replace_source(
        "acervo",
        "santos/francisco-de-assis",
        [
            ChunkInput(
                source_type="acervo",
                source_ref="santos/francisco-de-assis",
                title="São Francisco de Assis",
                text="Fundador da Ordem dos Frades Menores.",
            )
        ],
        [[1.0, 0.0, 0.0]],
    )
    use_case = AnswerQuestionUseCase(
        repo, _FakeEmbeddingGateway(), _FakeAnswerGenerator(should_fail=True)
    )

    # When / Then
    with pytest.raises(AnswerGenerationError) as exc_info:
        await use_case.execute("Quem fundou os franciscanos?")
    assert exc_info.value.code == "CHAT_INDISPONIVEL"


async def test_should_propagate_service_unavailable_from_gateway_without_double_wrapping() -> None:
    """Um gateway que já sabe que está desconfigurado levanta
    `ServiceUnavailableException` (ou uma subclasse) ele mesmo — o use case
    não encapsula numa segunda exceção genérica, porque não tem
    `try/except` nenhum."""

    class _MisconfiguredGateway:
        async def embed_documents(self, texts: list[str]) -> list[list[float]]:
            return []

        async def embed_query(self, question: str) -> list[float]:
            raise ServiceUnavailableException(
                message="sem chave", code="CHAT_INDISPONIVEL", details={"motivo": "sem_chave"}
            )

    repo = InMemoryRagRepository()
    use_case = AnswerQuestionUseCase(repo, _MisconfiguredGateway(), _FakeAnswerGenerator())

    # When / Then
    with pytest.raises(ServiceUnavailableException) as exc_info:
        await use_case.execute("Qualquer pergunta")
    assert exc_info.value.details == {"motivo": "sem_chave"}
