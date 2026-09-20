"""Testes do use case do chatbot isolados da camada HTTP — nenhum destes
sobe um `TestClient` nem chama Voyage/Claude de verdade, só fakes."""

from __future__ import annotations

import pytest

from app.application.chat.responder_pergunta_use_case import ResponderPerguntaUseCase
from app.core.exceptions import ServiceUnavailableException
from app.domain.chat.entities import ChunkInput, ChunkResult, FonteCitada
from app.domain.chat.relevance import NO_MATCH_MESSAGE
from app.infrastructure.chat.in_memory_repository import InMemoryRagRepository


class _FakeEmbeddingGateway:
    def __init__(self, vetor: list[float] | None = None, falhar: bool = False) -> None:
        self._vetor = vetor or [1.0, 0.0, 0.0]
        self._falhar = falhar

    async def embed_documents(self, textos: list[str]) -> list[list[float]]:
        return [self._vetor for _ in textos]

    async def embed_query(self, pergunta: str) -> list[float]:
        if self._falhar:
            raise RuntimeError("Voyage fora do ar")
        return self._vetor


class _FakeAnswerGenerator:
    def __init__(self, resposta: str = "resposta", falhar: bool = False) -> None:
        self._resposta = resposta
        self._falhar = falhar
        self.chamadas = 0

    async def generate(self, pergunta: str, trechos: list[ChunkResult]) -> str:
        self.chamadas += 1
        if self._falhar:
            raise RuntimeError("Claude fora do ar")
        return self._resposta


async def test_should_refuse_without_calling_generator_when_nothing_relevant() -> None:
    # Given — índice vazio, nenhum trecho bate
    repo = InMemoryRagRepository()
    generator = _FakeAnswerGenerator()
    use_case = ResponderPerguntaUseCase(repo, _FakeEmbeddingGateway(), generator)

    # When
    resultado = await use_case.execute("Qual a capital da França?")

    # Then
    assert resultado.resposta == NO_MATCH_MESSAGE
    assert resultado.fontes == []
    assert generator.chamadas == 0


async def test_should_answer_with_sources_when_a_relevant_chunk_exists() -> None:
    # Given
    repo = InMemoryRagRepository()
    await repo.replace_source(
        "acervo",
        "santos/francisco-de-assis",
        [
            ChunkInput(
                fonte_tipo="acervo",
                fonte_ref="santos/francisco-de-assis",
                titulo="São Francisco de Assis",
                texto="Fundador da Ordem dos Frades Menores.",
            )
        ],
        [[1.0, 0.0, 0.0]],
    )
    generator = _FakeAnswerGenerator(resposta="São Francisco fundou os franciscanos.")
    use_case = ResponderPerguntaUseCase(repo, _FakeEmbeddingGateway(), generator)

    # When
    resultado = await use_case.execute("Quem fundou os franciscanos?")

    # Then
    assert "franciscanos" in resultado.resposta
    assert generator.chamadas == 1
    assert resultado.fontes == [
        FonteCitada(
            titulo="São Francisco de Assis", categoria="santos", slug="francisco-de-assis"
        )
    ]


async def test_should_raise_service_unavailable_when_embedding_gateway_fails() -> None:
    # Given
    repo = InMemoryRagRepository()
    use_case = ResponderPerguntaUseCase(
        repo, _FakeEmbeddingGateway(falhar=True), _FakeAnswerGenerator()
    )

    # When / Then
    with pytest.raises(ServiceUnavailableException) as exc_info:
        await use_case.execute("Qualquer pergunta")
    assert exc_info.value.code == "CHAT_INDISPONIVEL"


async def test_should_raise_service_unavailable_when_answer_generator_fails() -> None:
    # Given — trecho relevante existe, mas o gerador falha
    repo = InMemoryRagRepository()
    await repo.replace_source(
        "acervo",
        "santos/francisco-de-assis",
        [
            ChunkInput(
                fonte_tipo="acervo",
                fonte_ref="santos/francisco-de-assis",
                titulo="São Francisco de Assis",
                texto="Fundador da Ordem dos Frades Menores.",
            )
        ],
        [[1.0, 0.0, 0.0]],
    )
    use_case = ResponderPerguntaUseCase(
        repo, _FakeEmbeddingGateway(), _FakeAnswerGenerator(falhar=True)
    )

    # When / Then
    with pytest.raises(ServiceUnavailableException) as exc_info:
        await use_case.execute("Quem fundou os franciscanos?")
    assert exc_info.value.code == "CHAT_INDISPONIVEL"


async def test_should_propagate_service_unavailable_from_gateway_without_double_wrapping() -> None:
    """Um gateway que já sabe que está desconfigurado levanta
    `ServiceUnavailableException` ele mesmo — o use case não deve
    encapsular numa segunda exceção genérica."""

    class _GatewaySemChave:
        async def embed_documents(self, textos: list[str]) -> list[list[float]]:
            return []

        async def embed_query(self, pergunta: str) -> list[float]:
            raise ServiceUnavailableException(
                message="sem chave", code="CHAT_INDISPONIVEL", details={"motivo": "sem_chave"}
            )

    repo = InMemoryRagRepository()
    use_case = ResponderPerguntaUseCase(repo, _GatewaySemChave(), _FakeAnswerGenerator())

    # When / Then
    with pytest.raises(ServiceUnavailableException) as exc_info:
        await use_case.execute("Qualquer pergunta")
    assert exc_info.value.details == {"motivo": "sem_chave"}
