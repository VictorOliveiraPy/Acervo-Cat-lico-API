"""Testes do use case do chatbot isolados da camada HTTP — nenhum destes
sobe um `TestClient` nem chama Voyage/DeepSeek de verdade, só fakes."""

from __future__ import annotations

import pytest

from app.application.chat.answer_question_use_case import AnswerQuestionUseCase
from app.core.exceptions import ServiceUnavailableException
from app.domain.chat.entities import ChunkInput, ChunkResult, CitedSource
from app.domain.chat.exceptions import AnswerGenerationError, EmbeddingGenerationError
from app.domain.chat.relevance import INSUFFICIENT_CONTEXT_MARKER, NO_MATCH_MESSAGE
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


async def test_should_hide_sources_when_model_signals_insufficient_context() -> None:
    """Bug real corrigido: um trecho pode passar no filtro de similaridade
    (parecido o bastante pra valer a chamada ao modelo) sem responder de
    verdade à pergunta — ex.: pergunta sobre "o padre" recupera um trecho
    sobre catequista. Quando o modelo sinaliza isso com
    INSUFFICIENT_CONTEXT_MARKER, a resposta final ao visitante é a mesma
    recusa coerente de sempre (NO_MATCH_MESSAGE), sem citar esse trecho
    como fonte de uma resposta que não responde à pergunta."""
    # Given
    repo = InMemoryRagRepository()
    await repo.replace_source(
        "acervo",
        "primeira-comunhao/papel-catequista",
        [
            ChunkInput(
                source_type="acervo",
                source_ref="primeira-comunhao/papel-catequista",
                title="O Papel do Catequista",
                text="O catequista acompanha a criança na preparação.",
            )
        ],
        [[1.0, 0.0, 0.0]],
    )
    generator = _FakeAnswerGenerator(answer=INSUFFICIENT_CONTEXT_MARKER)
    use_case = AnswerQuestionUseCase(repo, _FakeEmbeddingGateway(), generator)

    # When
    result = await use_case.execute("Quais são as funções do padre?")

    # Then
    assert result.answer == NO_MATCH_MESSAGE
    assert result.sources == []
    assert generator.calls == 1  # o trecho passou no filtro, a chamada aconteceu


async def test_should_detect_marker_even_with_stray_punctuation_around_it() -> None:
    """O prompt pede o marcador sozinho, mas um LLM não segue formatação à
    risca 100% das vezes (ex.: acrescenta um ponto final). A detecção
    precisa tolerar esse ruído, não exigir igualdade exata."""
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
    generator = _FakeAnswerGenerator(answer=f"{INSUFFICIENT_CONTEXT_MARKER}.")
    use_case = AnswerQuestionUseCase(repo, _FakeEmbeddingGateway(), generator)

    result = await use_case.execute("Pergunta qualquer")

    assert result.answer == NO_MATCH_MESSAGE
    assert result.sources == []


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
