"""Fake do índice de embeddings — mesma interface, sem Postgres.

Similaridade calculada em Python (cosseno), não em SQL/`pgvector` — só pra
testes e pro dry-run local do script de indexação.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.chat.entities import ChunkInput, ChunkResult
from app.domain.chat.repository import RagRepository


@dataclass
class InMemoryRagRepository(RagRepository):
    _rows: list[tuple[ChunkInput, list[float]]] = field(default_factory=list)

    async def replace_source(
        self,
        source_type: str,
        source_ref: str,
        chunks: list[ChunkInput],
        embeddings: list[list[float]],
    ) -> None:
        self._rows = [
            (row_chunk, row_emb)
            for row_chunk, row_emb in self._rows
            if not (row_chunk.source_type == source_type and row_chunk.source_ref == source_ref)
        ]
        self._rows.extend(zip(chunks, embeddings, strict=True))

    async def search(self, embedding: list[float], limit: int) -> list[ChunkResult]:
        def cosine(a: list[float], b: list[float]) -> float:
            dot = sum(x * y for x, y in zip(a, b, strict=True))
            norm_a = sum(x * x for x in a) ** 0.5
            norm_b = sum(y * y for y in b) ** 0.5
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return float(dot / (norm_a * norm_b))

        scored = sorted(
            (
                ChunkResult(
                    source_type=chunk.source_type,
                    source_ref=chunk.source_ref,
                    title=chunk.title,
                    text=chunk.text,
                    similarity=cosine(embedding, emb),
                )
                for chunk, emb in self._rows
            ),
            key=lambda r: r.similarity,
            reverse=True,
        )
        return scored[:limit]
