"""Rota HTTP do chatbot do acervo (`POST /api/chat`).

Registrado em `main.py` antes do router coringa do acervo, pelo mesmo
motivo de `interface.candles.router`/`interface.liturgy.router`: `/api/chat`
teria que competir com `/api/{categoria}` se viesse depois.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.application.chat.answer_question_use_case import AnswerQuestionUseCase
from app.core.exceptions import ServiceUnavailableException
from app.core.rate_limiting import RateLimiter, client_ip
from app.domain.chat.answer_generator import AnswerGenerator
from app.domain.chat.embedding_gateway import EmbeddingGateway
from app.domain.chat.repository import RagRepository
from app.infrastructure.chat.anthropic_answer_generator import AnthropicAnswerGenerator
from app.infrastructure.chat.voyage_embedding_gateway import VoyageEmbeddingGateway
from app.interface.chat.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Janela mais generosa que a do mural de velas (20s): uma conversa de
# verdade troca várias mensagens seguidas. Ainda assim conta, porque cada
# pergunta custa uma chamada de embedding + uma chamada ao Claude — dinheiro
# de verdade, ao contrário de listar o acervo.
_rate_limiter = RateLimiter(window_seconds=6.0)

# Sem estado próprio (não fala rede na criação) — uma instância por
# requisição não tem custo real.
_default_embedding_gateway = VoyageEmbeddingGateway()
_default_answer_generator = AnthropicAnswerGenerator()


def get_rag_repository(request: Request) -> RagRepository:
    """Lê o repositório setado no lifespan — `None` quando sem as chaves/banco."""
    repo: RagRepository | None = getattr(request.app.state, "rag_repository", None)
    if repo is None:
        raise ServiceUnavailableException(
            message="O chatbot está temporariamente indisponível.",
            code="CHAT_INDISPONIVEL",
        )
    return repo


def get_embedding_gateway(request: Request) -> EmbeddingGateway:
    """Gateway real por padrão; testes sobrescrevem via
    `app.state.embedding_gateway` com um fake."""
    return getattr(request.app.state, "embedding_gateway", None) or _default_embedding_gateway


def get_answer_generator(request: Request) -> AnswerGenerator:
    """Gateway real por padrão; testes sobrescrevem via
    `app.state.answer_generator` com um fake."""
    return getattr(request.app.state, "answer_generator", None) or _default_answer_generator


@router.post("", response_model=ChatResponse, summary="Pergunta ao chatbot do acervo")
async def chat(
    payload: ChatRequest,
    request: Request,
    repo: RagRepository = Depends(get_rag_repository),
    embedding_gateway: EmbeddingGateway = Depends(get_embedding_gateway),
    answer_generator: AnswerGenerator = Depends(get_answer_generator),
) -> ChatResponse:
    """Responde só com base em trechos recuperados do acervo — nunca do
    conhecimento próprio do modelo."""
    _rate_limiter.check(client_ip(request))
    use_case = AnswerQuestionUseCase(repo, embedding_gateway, answer_generator)
    answer = await use_case.execute(payload.pergunta)
    return ChatResponse.from_entity(answer)
