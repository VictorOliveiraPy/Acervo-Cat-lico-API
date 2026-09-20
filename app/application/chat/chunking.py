"""Quebra uma entrada do acervo em pedaços indexáveis (chunks).

Mora em `application`, não em `domain/chat`, porque orquestra entre dois
domínios: lê `AnyEntry` (o conteúdo do acervo) e produz `ChunkInput` (o
domínio do chat) — cruzar domínios é papel da camada de aplicação, não de
um domínio conhecer o outro diretamente. Usado só pelo script de indexação
(`scripts/indexar_acervo.py`), não pelo fluxo de pergunta/resposta.

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

from app.domain.chat.entities import ChunkInput
from app.models import AnyEntry

_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")
_INNER_WHITESPACE = re.compile(r"\s*\n\s*")


def split_paragraphs(body: str) -> list[str]:
    """Espelha `paragraphs()` do frontend: mesmos parágrafos, mesma ordem."""
    blocks = _PARAGRAPH_SPLIT.split(body)
    cleaned = (_INNER_WHITESPACE.sub(" ", block).strip() for block in blocks)
    return [block for block in cleaned if block]


def chunk_entry(entry: AnyEntry) -> list[ChunkInput]:
    """Quebra uma entrada em chunks: um para o resumo, um por parágrafo do corpo.

    O resumo entra como chunk à parte (não só embutido no primeiro parágrafo)
    porque muita pergunta simples ("o que é a Crisma") bate melhor contra a
    frase-resumo, feita pra isso, do que contra o primeiro parágrafo da
    explicação longa.
    """
    source_ref = f"{entry.categoria.value}/{entry.slug}"
    chunks = [
        ChunkInput(
            source_type="acervo",
            source_ref=source_ref,
            title=entry.titulo,
            text=entry.resumo,
        )
    ]
    chunks.extend(
        ChunkInput(
            source_type="acervo",
            source_ref=source_ref,
            title=entry.titulo,
            text=paragraph,
        )
        for paragraph in split_paragraphs(entry.corpo)
    )
    return chunks
