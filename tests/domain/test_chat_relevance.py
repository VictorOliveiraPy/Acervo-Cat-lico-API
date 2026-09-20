"""Testes de `select_relevant` — regra pura, sem I/O."""

from __future__ import annotations

from app.domain.chat.entities import ChunkResult
from app.domain.chat.relevance import SIMILARITY_THRESHOLD, select_relevant


def _chunk(similarity: float) -> ChunkResult:
    return ChunkResult(
        source_type="acervo",
        source_ref="santos/francisco-de-assis",
        title="São Francisco de Assis",
        text="Fundador da Ordem dos Frades Menores.",
        similarity=similarity,
    )


def test_should_keep_only_chunks_at_or_above_the_threshold() -> None:
    # Given
    chunks = [_chunk(0.9), _chunk(SIMILARITY_THRESHOLD), _chunk(0.1)]

    # When
    relevant = select_relevant(chunks)

    # Then
    assert len(relevant) == 2
    assert all(c.similarity >= SIMILARITY_THRESHOLD for c in relevant)
