"""DTOs Pydantic do chatbot — resposta HTTP, não a entidade de domínio."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.chat.entities import FonteCitada, RespostaChat

PERGUNTA_MAX_LENGTH = 500


class ChatRequest(BaseModel):
    """Pergunta enviada pelo visitante."""

    pergunta: str = Field(min_length=1, max_length=PERGUNTA_MAX_LENGTH)


class FonteCitadaResponse(BaseModel):
    """Um verbete usado para montar a resposta — sempre mostrado ao visitante."""

    titulo: str
    categoria: str
    slug: str

    @classmethod
    def from_entity(cls, fonte: FonteCitada) -> FonteCitadaResponse:
        return cls(titulo=fonte.titulo, categoria=fonte.categoria, slug=fonte.slug)


class ChatResponse(BaseModel):
    """Resposta do chatbot: o texto gerado e as fontes que o sustentam."""

    resposta: str
    fontes: list[FonteCitadaResponse]

    @classmethod
    def from_entity(cls, resposta: RespostaChat) -> ChatResponse:
        return cls(
            resposta=resposta.resposta,
            fontes=[FonteCitadaResponse.from_entity(f) for f in resposta.fontes],
        )
