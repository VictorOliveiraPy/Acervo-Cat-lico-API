"""Exceções do domínio do chatbot — puro Python, sem FastAPI.

Levantadas pelos gateways (`app.infrastructure.chat.voyage_embedding_gateway`,
`app.infrastructure.chat.deepseek_answer_generator`) quando o provedor
externo falha — já são `AppException`, então `AnswerQuestionUseCase` não
precisa de `try/except`: a exceção sobe sozinha até o handler global
(`app.interface.exception_handlers`).
"""

from __future__ import annotations

from app.core.exceptions import ServiceUnavailableException


class EmbeddingGenerationError(ServiceUnavailableException):
    """Falha ao gerar o embedding da pergunta (sem chave configurada, rede,
    HTTP 5xx da Voyage)."""

    def __init__(self) -> None:
        super().__init__(
            message="Não foi possível processar a pergunta agora. Tente novamente em instantes.",
            code="CHAT_INDISPONIVEL",
        )


class AnswerGenerationError(ServiceUnavailableException):
    """Falha ao gerar a resposta (sem chave configurada, rede, HTTP 5xx da DeepSeek)."""

    def __init__(self) -> None:
        super().__init__(
            message="Não foi possível gerar uma resposta agora. Tente novamente em instantes.",
            code="CHAT_INDISPONIVEL",
        )
