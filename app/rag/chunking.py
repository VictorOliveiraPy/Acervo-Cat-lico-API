"""Quebra uma entrada do acervo em pedaços indexáveis (chunks).

Granularidade por parágrafo, não por verbete inteiro: um verbete grande
(alguns têm corpo de 10+ parágrafos) misturado num vetor só perde precisão —
a pergunta "quando nasceu Santo Agostinho" bate melhor contra um parágrafo
específico do que contra a biografia inteira comprimida numa média vetorial.

O regex de parágrafo é o mesmo do frontend (`lib/entryDisplay.ts:paragraphs`),
de propósito: os dois lados têm que quebrar o mesmo `corpo` do mesmo jeito,
senão o texto citado pelo chatbot pode não bater com o que a página do
verbete efetivamente mostra.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.models import AnyEntry

_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")
_INNER_WHITESPACE = re.compile(r"\s*\n\s*")


def split_paragraphs(corpo: str) -> list[str]:
    """Espelha `paragraphs()` do frontend: mesmos parágrafos, mesma ordem."""
    blocks = _PARAGRAPH_SPLIT.split(corpo)
    cleaned = (_INNER_WHITESPACE.sub(" ", block).strip() for block in blocks)
    return [block for block in cleaned if block]


@dataclass(frozen=True)
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


def chunk_entry(entry: AnyEntry) -> list[ChunkInput]:
    """Quebra uma entrada em chunks: um para o resumo, um por parágrafo do corpo.

    O resumo entra como chunk à parte (não só embutido no primeiro parágrafo)
    porque muita pergunta simples ("o que é a Crisma") bate melhor contra a
    frase-resumo, feita pra isso, do que contra o primeiro parágrafo da
    explicação longa.
    """
    fonte_ref = f"{entry.categoria.value}/{entry.slug}"
    chunks = [
        ChunkInput(
            fonte_tipo="acervo",
            fonte_ref=fonte_ref,
            titulo=entry.titulo,
            texto=entry.resumo,
        )
    ]
    chunks.extend(
        ChunkInput(
            fonte_tipo="acervo",
            fonte_ref=fonte_ref,
            titulo=entry.titulo,
            texto=paragrafo,
        )
        for paragrafo in split_paragraphs(entry.corpo)
    )
    return chunks
