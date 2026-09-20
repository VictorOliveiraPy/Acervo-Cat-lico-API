"""Caso de uso: responder uma pergunta só com base no que o acervo tem.

Regra de ouro do módulo: o modelo só vê os trechos recuperados do acervo —
ver `AnthropicAnswerGenerator`/`SYSTEM_PROMPT` pra onde isso é de fato
imposto ao LLM.
"""

from __future__ import annotations

from app.core.config import settings
from app.domain.chat.answer_generator import AnswerGenerator
from app.domain.chat.embedding_gateway import EmbeddingGateway
from app.domain.chat.entities import ChatAnswer, ChunkResult, CitedSource
from app.domain.chat.relevance import NO_MATCH_MESSAGE, select_relevant
from app.domain.chat.repository import RagRepository


def _unique_sources(chunks: list[ChunkResult]) -> list[CitedSource]:
    """Uma citação por verbete, não uma por chunk — vários parágrafos do
    mesmo verbete podem aparecer entre os trechos mais parecidos."""
    seen: dict[str, CitedSource] = {}
    for chunk in chunks:
        if chunk.source_ref in seen:
            continue
        category, _, slug = chunk.source_ref.partition("/")
        seen[chunk.source_ref] = CitedSource(title=chunk.title, category=category, slug=slug)
    return list(seen.values())


class AnswerQuestionUseCase:
    """Orquestra embedding → busca → filtro de relevância → geração.

    Falha do embedding gateway ou do gerador de resposta já chega aqui como
    `EmbeddingGenerationError`/`AnswerGenerationError` (o gateway/gerador
    que traduz o erro de rede/SDK — ver `app.infrastructure.chat`), então
    não há nada pra este método capturar.
    """

    def __init__(
        self,
        repository: RagRepository,
        embedding_gateway: EmbeddingGateway,
        answer_generator: AnswerGenerator,
    ) -> None:
        self._repository = repository
        self._embedding_gateway = embedding_gateway
        self._answer_generator = answer_generator

    async def execute(self, question: str) -> ChatAnswer:
        embedding = await self._embedding_gateway.embed_query(question)
        chunks = await self._repository.search(
            embedding, limit=settings.chat_max_context_chunks
        )
        relevant = select_relevant(chunks)

        # Sem trecho relevante, nem chama o gerador — poupa uma chamada paga
        # que já sabemos que não tem como responder bem.
        if not relevant:
            return ChatAnswer(answer=NO_MATCH_MESSAGE, sources=[])

        answer = await self._answer_generator.generate(question, relevant)
        return ChatAnswer(answer=answer, sources=_unique_sources(relevant))
