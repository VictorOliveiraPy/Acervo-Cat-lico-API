"""Acesso ao índice de embeddings do chatbot (`rag_chunks`) em Postgres.

`register_vector` é chamado por conexão, não uma vez só no pool: registrar
no nível do pool (via `init=`) exigiria que a extensão `vector` já existisse
no banco no instante em que a primeira conexão fosse aberta — em um banco
novo, `create_schema` é quem cria a extensão, e isso só acontece depois que
o pool já existe. Registrar por conexão evita essa dependência de ordem.
"""

from __future__ import annotations

import asyncpg
from pgvector.asyncpg import register_vector

from app.domain.chat.entities import ChunkInput, ChunkResult
from app.domain.chat.repository import RagRepository


class PostgresRagRepository(RagRepository):
    """Implementação de produção, sobre um pool `asyncpg` com `pgvector`."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    @staticmethod
    async def create_schema(pool: asyncpg.Pool) -> None:
        """Habilita a extensão e cria a tabela/índices se não existirem.

        Sem índice `ivfflat`/`hnsw` de propósito nesta fase: com alguns
        milhares de linhas (1.043 verbetes, poucos chunks cada), busca exata
        por `ORDER BY embedding <=> $1` é rápida o bastante — um índice
        aproximado só compensa a partir de dezenas de milhares de vetores.
        """
        await pool.execute("CREATE EXTENSION IF NOT EXISTS vector")
        await pool.execute(
            """
            CREATE TABLE IF NOT EXISTS rag_chunks (
                id BIGSERIAL PRIMARY KEY,
                fonte_tipo TEXT NOT NULL,
                fonte_ref TEXT NOT NULL,
                titulo TEXT NOT NULL,
                texto TEXT NOT NULL,
                embedding VECTOR(512) NOT NULL,
                criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        await pool.execute(
            """
            CREATE INDEX IF NOT EXISTS rag_chunks_fonte_idx
            ON rag_chunks (fonte_tipo, fonte_ref)
            """
        )

    async def replace_source(
        self,
        fonte_tipo: str,
        fonte_ref: str,
        chunks: list[ChunkInput],
        embeddings: list[list[float]],
    ) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks e embeddings precisam ter o mesmo tamanho")

        async with self._pool.acquire() as conn:
            await register_vector(conn)
            async with conn.transaction():
                await conn.execute(
                    "DELETE FROM rag_chunks WHERE fonte_tipo = $1 AND fonte_ref = $2",
                    fonte_tipo,
                    fonte_ref,
                )
                await conn.executemany(
                    """
                    INSERT INTO rag_chunks (fonte_tipo, fonte_ref, titulo, texto, embedding)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    [
                        (chunk.fonte_tipo, chunk.fonte_ref, chunk.titulo, chunk.texto, emb)
                        for chunk, emb in zip(chunks, embeddings, strict=True)
                    ],
                )

    async def search(self, embedding: list[float], limit: int) -> list[ChunkResult]:
        async with self._pool.acquire() as conn:
            await register_vector(conn)
            rows = await conn.fetch(
                """
                SELECT fonte_tipo, fonte_ref, titulo, texto,
                       1 - (embedding <=> $1) AS similaridade
                FROM rag_chunks
                ORDER BY embedding <=> $1
                LIMIT $2
                """,
                embedding,
                limit,
            )
        return [
            ChunkResult(
                fonte_tipo=row["fonte_tipo"],
                fonte_ref=row["fonte_ref"],
                titulo=row["titulo"],
                texto=row["texto"],
                similaridade=row["similaridade"],
            )
            for row in rows
        ]
