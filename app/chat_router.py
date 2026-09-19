"""Rota HTTP do chatbot do acervo (`POST /api/chat`).

Registrado em `main.py` antes do router coringa do acervo, pelo mesmo
motivo de `velas_router`/`liturgia_router`: `/api/chat` teria que competir
com `/api/{categoria}` se viesse depois.

`RateLimiter`/`client_ip` vêm de `app.core.rate_limiting` — cross-cutting,
não específico de nenhum domínio; cada endpoint cria sua própria instância
com a janela que fizer sentido.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request

from app.core.config import settings
from app.core.exceptions import ServiceUnavailableException
from app.core.rate_limiting import RateLimiter, client_ip
from app.rag.embeddings import embed_query
from app.rag.generation import generate_answer, select_relevant
from app.rag.models import ChatRequest, ChatResponse, FonteCitada
from app.rag.repository import RagRepository, require_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Janela mais generosa que a do mural de velas (20s): uma conversa de
# verdade troca várias mensagens seguidas. Ainda assim conta, porque cada
# pergunta custa uma chamada de embedding + uma chamada ao Claude — dinheiro
# de verdade, ao contrário de listar o acervo.
_rate_limiter = RateLimiter(window_seconds=6.0)


def get_rag_repository(request: Request) -> RagRepository:
    """Lê o repositório setado no lifespan — `None` quando sem as chaves/banco."""
    repo: RagRepository | None = getattr(request.app.state, "rag_repository", None)
    return require_repository(repo)


def _fontes_unicas(trechos: list) -> list[FonteCitada]:
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


@router.post("", response_model=ChatResponse, summary="Pergunta ao chatbot do acervo")
async def chat(
    payload: ChatRequest,
    request: Request,
    repo: RagRepository = Depends(get_rag_repository),
) -> ChatResponse:
    """Responde só com base em trechos recuperados do acervo — nunca do
    conhecimento próprio do modelo. Ver `app/rag/generation.py`."""
    _rate_limiter.check(client_ip(request))

    try:
        embedding = await embed_query(payload.pergunta)
    except ServiceUnavailableException:
        raise
    except Exception as exc:
        logger.exception("Falha ao gerar embedding da pergunta")
        raise ServiceUnavailableException(
            message="Não foi possível processar a pergunta agora. Tente novamente em instantes.",
            code="CHAT_INDISPONIVEL",
        ) from exc

    trechos = await repo.search(embedding, limit=settings.chat_max_context_chunks)
    relevantes = select_relevant(trechos)
    resposta = await generate_answer(payload.pergunta, relevantes)

    return ChatResponse(resposta=resposta, fontes=_fontes_unicas(relevantes))
