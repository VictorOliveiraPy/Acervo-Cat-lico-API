"""Entidades do domínio do chatbot — puro Python, sem Pydantic/FastAPI."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChunkInput:
    """Um pedaço de texto pronto pra virar embedding e ser indexado."""

    source_type: str
    """`"acervo"` nesta fase — `"livro"` quando a ingestão de PDF existir."""
    source_ref: str
    """Identifica a origem: `"{categoria}/{slug}"` pro acervo."""
    title: str
    """Título do verbete — vai na citação mostrada ao visitante."""
    text: str
    """O conteúdo do pedaço em si — o que vira embedding."""


@dataclass(frozen=True, slots=True)
class ChunkResult:
    """Um pedaço recuperado do índice, já com a similaridade da busca."""

    source_type: str
    source_ref: str
    title: str
    text: str
    similarity: float
    """Cosseno de similaridade (1 = idêntico, 0 = ortogonal/sem relação)."""


@dataclass(frozen=True, slots=True)
class CitedSource:
    """Um verbete usado para montar a resposta — sempre mostrado ao visitante.

    `category`/`slug`, não uma URL pronta: quem monta URL é o frontend
    (`entryPath()`), a mesma regra de qualquer entrada do acervo.
    """

    title: str
    category: str
    slug: str


@dataclass(frozen=True, slots=True)
class ChatAnswer:
    """Resposta do chatbot: o texto gerado e as fontes que o sustentam.

    `sources` vem vazia quando nada no acervo bateu com a pergunta — nesse
    caso `answer` é a recusa educada (`NO_MATCH_MESSAGE`), não uma tentativa
    de responder mesmo assim.
    """

    answer: str
    sources: list[CitedSource]
