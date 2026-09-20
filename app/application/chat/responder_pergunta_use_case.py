"""Caso de uso: responder uma pergunta só com base no que o acervo tem.

Regra de ouro do módulo: o modelo só vê os trechos recuperados do acervo —
ver `AnthropicAnswerGenerator`/`SYSTEM_PROMPT` pra onde isso é de fato
imposto ao LLM.
"""

from __future__ import annotations

import logging

from app.core.config import settings
from app.core.exceptions import ServiceUnavailableException
from app.domain.chat.answer_generator import AnswerGenerator
from app.domain.chat.embedding_gateway import EmbeddingGateway
from app.domain.chat.entities import ChunkResult, FonteCitada, RespostaChat
from app.domain.chat.relevance import NO_MATCH_MESSAGE, select_relevant
from app.domain.chat.repository import RagRepository

logger = logging.getLogger(__name__)


def _fontes_unicas(trechos: list[ChunkResult]) -> list[FonteCitada]:
    """Uma citação por verbete, não uma por chunk — vários parágrafos do
    mesmo verbete podem aparecer entre os trechos mais parecidos."""
    vistas: dict[str, FonteCitada] = {}
    for trecho in trechos:
        if trecho.fonte_ref in vistas:
            continue
        categoria, _, slug = trecho.fonte_ref.partition("/")
        vistas[trecho.fonte_ref] = FonteCitada(
            titulo=trecho.titulo, categoria=categoria, slug=slug
        )
    return list(vistas.values())


class ResponderPerguntaUseCase:
    """Orquestra embedding → busca → filtro de relevância → geração.

    Falha do embedding gateway ou do gerador de resposta (rede, HTTP 5xx,
    SDK malformado) vira `ServiceUnavailableException` — nunca um 500 cru
    pro cliente por causa de um provedor de IA fora do ar. Um provedor que
    já sabe que está desconfigurado (sem chave de API) pode levantar
    `ServiceUnavailableException` ele mesmo; qualquer outra exceção é
    tratada aqui como falha inesperada.
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

    async def execute(self, pergunta: str) -> RespostaChat:
        try:
            embedding = await self._embedding_gateway.embed_query(pergunta)
        except ServiceUnavailableException:
            raise
        except Exception as exc:
            logger.exception("Falha ao gerar embedding da pergunta")
            raise ServiceUnavailableException(
                message="Não foi possível processar a pergunta agora. Tente novamente em instantes.",
                code="CHAT_INDISPONIVEL",
            ) from exc

        trechos = await self._repository.search(
            embedding, limit=settings.chat_max_context_chunks
        )
        relevantes = select_relevant(trechos)

        # Sem trecho relevante, nem chama o gerador — poupa uma chamada paga
        # que já sabemos que não tem como responder bem.
        if not relevantes:
            return RespostaChat(resposta=NO_MATCH_MESSAGE, fontes=[])

        try:
            resposta = await self._answer_generator.generate(pergunta, relevantes)
        except ServiceUnavailableException:
            raise
        except Exception as exc:
            logger.exception("Falha ao chamar a API do Claude")
            raise ServiceUnavailableException(
                message="Não foi possível gerar uma resposta agora. Tente novamente em instantes.",
                code="CHAT_INDISPONIVEL",
            ) from exc

        return RespostaChat(resposta=resposta, fontes=_fontes_unicas(relevantes))
