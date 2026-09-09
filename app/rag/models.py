"""Contrato HTTP do chatbot (`POST /api/chat`) e tipos internos de busca.

`categoria`/`slug` em `FonteCitada`, não uma URL pronta: a API nunca monta
URL (o frontend tem `entryPath()` pra isso, ver `lib/categories.ts`) — mesmo
padrão já usado em toda entrada do acervo.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field

PERGUNTA_MAX_LENGTH = 500


class ChatRequest(BaseModel):
    """Pergunta enviada pelo visitante."""

    pergunta: str = Field(min_length=1, max_length=PERGUNTA_MAX_LENGTH)


class FonteCitada(BaseModel):
    """Um verbete usado para montar a resposta — sempre mostrado ao visitante."""

    titulo: str
    categoria: str
    slug: str


class ChatResponse(BaseModel):
    """Resposta do chatbot: o texto gerado e as fontes que o sustentam.

    `fontes` vem vazia quando nada no acervo bateu com a pergunta — nesse
    caso `resposta` é a recusa educada, não uma tentativa de responder
    mesmo assim (ver `app/rag/generation.py`).
    """

    resposta: str
    fontes: list[FonteCitada]


@dataclass(frozen=True)
class ChunkResult:
    """Um pedaço recuperado do índice, já com a similaridade da busca."""

    fonte_tipo: str
    fonte_ref: str
    titulo: str
    texto: str
    similaridade: float
    """Cosseno de similaridade (1 = idêntico, 0 = ortogonal/sem relação)."""
