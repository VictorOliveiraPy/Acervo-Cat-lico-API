"""Entidades do domínio do chatbot — puro Python, sem Pydantic/FastAPI."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChunkInput:
    """Um pedaço de texto pronto pra virar embedding e ser indexado."""

    fonte_tipo: str
    """`"acervo"` nesta fase — `"livro"` quando a ingestão de PDF existir."""
    fonte_ref: str
    """Identifica a origem: `"{categoria}/{slug}"` pro acervo."""
    titulo: str
    """Título do verbete — vai na citação mostrada ao visitante."""
    texto: str
    """O conteúdo do pedaço em si — o que vira embedding."""


@dataclass(frozen=True, slots=True)
class ChunkResult:
    """Um pedaço recuperado do índice, já com a similaridade da busca."""

    fonte_tipo: str
    fonte_ref: str
    titulo: str
    texto: str
    similaridade: float
    """Cosseno de similaridade (1 = idêntico, 0 = ortogonal/sem relação)."""


@dataclass(frozen=True, slots=True)
class FonteCitada:
    """Um verbete usado para montar a resposta — sempre mostrado ao visitante.

    `categoria`/`slug`, não uma URL pronta: quem monta URL é o frontend
    (`entryPath()`), a mesma regra de qualquer entrada do acervo.
    """

    titulo: str
    categoria: str
    slug: str


@dataclass(frozen=True, slots=True)
class RespostaChat:
    """Resposta do chatbot: o texto gerado e as fontes que o sustentam.

    `fontes` vem vazia quando nada no acervo bateu com a pergunta — nesse
    caso `resposta` é a recusa educada (`NO_MATCH_MESSAGE`), não uma
    tentativa de responder mesmo assim.
    """

    resposta: str
    fontes: list[FonteCitada]
