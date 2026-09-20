"""DTOs Pydantic do chatbot — resposta HTTP, não a entidade de domínio.

Os nomes de CAMPO abaixo (`pergunta`, `resposta`, `fontes`, `titulo`,
`categoria`) continuam em português de propósito: são as chaves do JSON que
o frontend já consome em produção.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.chat.entities import ChatAnswer, CitedSource

QUESTION_MAX_LENGTH = 500


class ChatRequest(BaseModel):
    """Pergunta enviada pelo visitante."""

    pergunta: str = Field(min_length=1, max_length=QUESTION_MAX_LENGTH)


class CitedSourceResponse(BaseModel):
    """Um verbete usado para montar a resposta — sempre mostrado ao visitante."""

    titulo: str
    categoria: str
    slug: str

    @classmethod
    def from_entity(cls, source: CitedSource) -> CitedSourceResponse:
        return cls(titulo=source.title, categoria=source.category, slug=source.slug)


class ChatResponse(BaseModel):
    """Resposta do chatbot: o texto gerado e as fontes que o sustentam."""

    resposta: str
    fontes: list[CitedSourceResponse]

    @classmethod
    def from_entity(cls, answer: ChatAnswer) -> ChatResponse:
        return cls(
            resposta=answer.answer,
            fontes=[CitedSourceResponse.from_entity(s) for s in answer.sources],
        )
