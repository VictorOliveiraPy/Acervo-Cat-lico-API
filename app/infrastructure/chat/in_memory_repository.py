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

    async def search(self, embedding: list[float], question: str, limit: int) -> list[ChunkResult]:
        """Espelha a fusão por ranking (RRF) do Postgres (ver
        `PostgresRagRepository.search`): combina a *posição* no ranking por
        cosseno com a posição no ranking por palavra literal da pergunta —
        não o score bruto, senão um match textual nunca venceria um cosseno
        mais alto vindo de um chunk só tangencialmente parecido."""

        def cosine(a: list[float], b: list[float]) -> float:
            dot = sum(x * y for x, y in zip(a, b, strict=True))
            norm_a = sum(x * x for x in a) ** 0.5
            norm_b = sum(y * y for y in b) ** 0.5
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return float(dot / (norm_a * norm_b))

        palavras = {p.lower() for p in question.split() if len(p) >= 4}

        def bate_texto_livre(chunk: ChunkInput) -> bool:
            alvo = f"{chunk.title} {chunk.text}".lower()
            return any(palavra in alvo for palavra in palavras)

        candidatos_por_via = max(limit * 3, 15)
        todos = [
            ChunkResult(
                source_type=chunk.source_type,
                source_ref=chunk.source_ref,
                title=chunk.title,
                text=chunk.text,
                similarity=cosine(embedding, emb),
            )
            for chunk, emb in self._rows
        ]

        por_vetor = sorted(todos, key=lambda r: r.similarity, reverse=True)[:candidatos_por_via]
        por_texto = [
            resultado
            for resultado, (chunk, _emb) in zip(todos, self._rows, strict=True)
            if bate_texto_livre(chunk)
        ][:candidatos_por_via]

        pontuacao_rrf: dict[tuple[str, str], float] = {}
        resultado_por_chave: dict[tuple[str, str], ChunkResult] = {}
        for ranking in (por_vetor, por_texto):
            for posicao, resultado in enumerate(ranking, start=1):
                chave = (resultado.source_ref, resultado.text)
                resultado_por_chave[chave] = resultado
                pontuacao_rrf[chave] = pontuacao_rrf.get(chave, 0.0) + 1.0 / (60 + posicao)

        chaves_ordenadas = sorted(
            pontuacao_rrf, key=lambda chave: pontuacao_rrf[chave], reverse=True
        )
        return [resultado_por_chave[chave] for chave in chaves_ordenadas[:limit]]
