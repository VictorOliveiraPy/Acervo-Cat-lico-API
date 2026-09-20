"""Testes de `select_relevant` — regra pura, sem I/O."""

from __future__ import annotations

from app.domain.chat.entities import ChunkResult
from app.domain.chat.relevance import SIMILARITY_THRESHOLD, select_relevant


def _chunk(similaridade: float) -> ChunkResult:
    return ChunkResult(
        fonte_tipo="acervo",
        fonte_ref="santos/francisco-de-assis",
        titulo="São Francisco de Assis",
        texto="Fundador da Ordem dos Frades Menores.",
        similaridade=similaridade,
    )


def test_should_keep_only_chunks_at_or_above_the_threshold() -> None:
    # Given
    trechos = [_chunk(0.9), _chunk(SIMILARITY_THRESHOLD), _chunk(0.1)]

    # When
    relevantes = select_relevant(trechos)

    # Then
    assert len(relevantes) == 2
    assert all(t.similaridade >= SIMILARITY_THRESHOLD for t in relevantes)
