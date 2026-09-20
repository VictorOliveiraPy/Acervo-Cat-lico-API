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
        fonte_tipo: str,
        fonte_ref: str,
        chunks: list[ChunkInput],
        embeddings: list[list[float]],
    ) -> None:
        self._rows = [
            (row_chunk, row_emb)
            for row_chunk, row_emb in self._rows
            if not (row_chunk.fonte_tipo == fonte_tipo and row_chunk.fonte_ref == fonte_ref)
        ]
        self._rows.extend(zip(chunks, embeddings, strict=True))

    async def search(self, embedding: list[float], limit: int) -> list[ChunkResult]:
        def cosseno(a: list[float], b: list[float]) -> float:
            dot = sum(x * y for x, y in zip(a, b, strict=True))
            norm_a = sum(x * x for x in a) ** 0.5
            norm_b = sum(y * y for y in b) ** 0.5
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return float(dot / (norm_a * norm_b))

        scored = sorted(
            (
                ChunkResult(
                    fonte_tipo=chunk.fonte_tipo,
                    fonte_ref=chunk.fonte_ref,
                    titulo=chunk.titulo,
                    texto=chunk.texto,
                    similaridade=cosseno(embedding, emb),
                )
                for chunk, emb in self._rows
            ),
            key=lambda r: r.similaridade,
            reverse=True,
        )
        return scored[:limit]
