"""Acesso ao índice de embeddings do chatbot (`rag_chunks`) em Postgres.

`register_vector` é chamado por conexão, não uma vez só no pool: registrar
no nível do pool (via `init=`) exigiria que a extensão `vector` já existisse
no banco no instante em que a primeira conexão fosse aberta — em um banco
novo, `create_schema` é quem cria a extensão, e isso só acontece depois que
o pool já existe. Registrar por conexão evita essa dependência de ordem.

As colunas da tabela (`fonte_tipo`, `fonte_ref`, `titulo`, `texto`) e o
alias `similaridade` continuam em português de propósito: é o schema já
gravado em produção — o mapeamento pros nomes em inglês da entidade
acontece só aqui.
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
        # Índice de texto (GIN) pra busca híbrida — ver docstring de `search`.
        await pool.execute(
            """
            CREATE INDEX IF NOT EXISTS rag_chunks_texto_fts_idx
            ON rag_chunks USING GIN (to_tsvector('portuguese', titulo || ' ' || texto))
            """
        )

    async def replace_source(
        self,
        source_type: str,
        source_ref: str,
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
                    source_type,
                    source_ref,
                )
                await conn.executemany(
                    """
                    INSERT INTO rag_chunks (fonte_tipo, fonte_ref, titulo, texto, embedding)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    [
                        (chunk.source_type, chunk.source_ref, chunk.title, chunk.text, emb)
                        for chunk, emb in zip(chunks, embeddings, strict=True)
                    ],
                )

    async def search(self, embedding: list[float], question: str, limit: int) -> list[ChunkResult]:
        """Busca híbrida por fusão de ranking (RRF — Reciprocal Rank Fusion):
        combina a *posição* de cada chunk no ranking vetorial com a posição
        no ranking por texto (`plainto_tsquery`), não o score bruto — um
        cosseno de 0.57 nunca venceria um de 0.64 numa soma direta de score,
        mas pode vencer se estiver em 1º no ranking textual contra um 5º
        lugar no vetorial. `similaridade` no resultado continua sendo o
        cosseno real (não a pontuação RRF), porque é isso que
        `SIMILARITY_THRESHOLD` em `relevance.py` espera comparar.

        Motivação (achado real, não teórico): pra perguntas curtas com nome
        próprio ou termo doutrinário ("Padre", "Ordem"), o embedding sozinho
        enterra o verbete certo atrás de biografias de santos que só citam a
        palavra de passagem — o texto literal bate onde o embedding erra.
        Sem `question` casando nada (ou vazia), a fusão vira só a busca
        vetorial de sempre (RRF de uma via só preserva a ordem original).

        Candidatos por via = `max(limit * 3, 15)`: dá margem pra um bom match
        textual entrar mesmo se não estivesse no top vetorial, sem inflar
        demais a query. `60` na fórmula RRF é a constante usual da técnica
        (achata a diferença entre 1º e 2º lugar; não é sensível a ajuste
        fino).

        `ts_rank` empata muito pra termo único (a maioria das perguntas
        curtas) — o desempate por distância de embedding evita que a ordem
        vire loteria entre documentos igualmente "1 menção da palavra", e
        deixa o que é mais parecido de verdade na frente dentro do empate.
        """
        candidatos_por_via = max(limit * 3, 15)
        async with self._pool.acquire() as conn:
            await register_vector(conn)
            rows = await conn.fetch(
                """
                WITH vetor AS (
                    SELECT fonte_tipo, fonte_ref, titulo, texto,
                           1 - (embedding <=> $1) AS similaridade,
                           row_number() OVER (ORDER BY embedding <=> $1) AS posicao
                    FROM rag_chunks
                    ORDER BY embedding <=> $1
                    LIMIT $3
                ),
                texto_livre AS (
                    SELECT fonte_tipo, fonte_ref, titulo, texto,
                           1 - (embedding <=> $1) AS similaridade,
                           row_number() OVER (ORDER BY ts_rank(
                               to_tsvector('portuguese', titulo || ' ' || texto),
                               plainto_tsquery('portuguese', $2)
                           ) DESC, embedding <=> $1) AS posicao
                    FROM rag_chunks
                    WHERE to_tsvector('portuguese', titulo || ' ' || texto)
                          @@ plainto_tsquery('portuguese', $2)
                    ORDER BY ts_rank(
                        to_tsvector('portuguese', titulo || ' ' || texto),
                        plainto_tsquery('portuguese', $2)
                    ) DESC, embedding <=> $1
                    LIMIT $3
                ),
                combinado AS (
                    SELECT fonte_tipo, fonte_ref, titulo, texto, similaridade,
                           1.0 / (60 + posicao) AS pontuacao_rrf
                    FROM vetor
                    UNION ALL
                    SELECT fonte_tipo, fonte_ref, titulo, texto, similaridade,
                           1.0 / (60 + posicao) AS pontuacao_rrf
                    FROM texto_livre
                )
                SELECT fonte_tipo, fonte_ref, titulo, texto,
                       max(similaridade) AS similaridade
                FROM combinado
                GROUP BY fonte_tipo, fonte_ref, titulo, texto
                ORDER BY sum(pontuacao_rrf) DESC
                LIMIT $4
                """,
                embedding,
                question,
                candidatos_por_via,
                limit,
            )
        return [
            ChunkResult(
                source_type=row["fonte_tipo"],
                source_ref=row["fonte_ref"],
                title=row["titulo"],
                text=row["texto"],
                similarity=row["similaridade"],
            )
            for row in rows
        ]
