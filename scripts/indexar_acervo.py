#!/usr/bin/env python3
"""Indexa o acervo inteiro (ou uma categoria) no banco de embeddings do chatbot.

Uso:
    python -m scripts.indexar_acervo
    python -m scripts.indexar_acervo --categoria santos

Precisa de `DATABASE_URL` e `VOYAGE_API_KEY` no ambiente (mesmo `.env` que a
API usa). Roda uma vez pra popular o índice, e de novo sempre que o conteúdo
de `app/data/*.json` mudar — `replace_source` apaga os chunks antigos de
cada verbete antes de gravar os novos, então rodar de novo não duplica nada.

Fase 1 do chatbot (ver plano): só o acervo. Livros em PDF entram num script
próprio (`scripts/indexar_pdf.py`) quando essa fase começar.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

import asyncpg

from app.application.chat.chunking import chunk_entry
from app.core.config import settings
from app.domain.chat.entities import ChunkInput
from app.infrastructure.acervo.json_repository import repository
from app.infrastructure.chat.postgres_repository import PostgresRagRepository
from app.infrastructure.chat.voyage_embedding_gateway import VoyageEmbeddingGateway

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("indexar_acervo")

# A Voyage aceita lote grande, mas manter moderado evita um erro de rede
# jogar fora o embedding de 1000 chunks de uma vez.
BATCH_SIZE = 64


async def _indexar_entrada(
    repo: PostgresRagRepository,
    gateway: VoyageEmbeddingGateway,
    chunks: list[ChunkInput],
) -> None:
    if not chunks:
        return
    textos = [chunk.text for chunk in chunks]
    embeddings: list[list[float]] = []
    for inicio in range(0, len(textos), BATCH_SIZE):
        lote = textos[inicio : inicio + BATCH_SIZE]
        embeddings.extend(await gateway.embed_documents(lote))
    fonte_tipo = chunks[0].source_type
    fonte_ref = chunks[0].source_ref
    await repo.replace_source(fonte_tipo, fonte_ref, chunks, embeddings)


async def main(categoria_filtro: str | None) -> None:
    if not settings.database_url:
        sys.exit("DATABASE_URL não configurada.")
    if not settings.voyage_api_key:
        sys.exit("VOYAGE_API_KEY não configurada.")

    repository.load()
    entradas = repository.all_entries()
    if categoria_filtro:
        entradas = [e for e in entradas if e.categoria.value == categoria_filtro]
        if not entradas:
            sys.exit(f"Nenhuma entrada encontrada para a categoria '{categoria_filtro}'.")

    logger.info("Indexando %d entradas...", len(entradas))

    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=5)
    try:
        await PostgresRagRepository.create_schema(pool)
        repo = PostgresRagRepository(pool)
        gateway = VoyageEmbeddingGateway()

        total_chunks = 0
        for i, entry in enumerate(entradas, start=1):
            chunks = chunk_entry(entry)
            await _indexar_entrada(repo, gateway, chunks)
            total_chunks += len(chunks)
            if i % 25 == 0 or i == len(entradas):
                logger.info("  %d/%d verbetes (%d chunks até aqui)", i, len(entradas), total_chunks)
    finally:
        await pool.close()

    logger.info("Concluído: %d verbetes, %d chunks indexados.", len(entradas), total_chunks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--categoria",
        default=None,
        help="Reindexar só uma categoria (slug, ex.: santos) em vez do acervo inteiro.",
    )
    args = parser.parse_args()
    asyncio.run(main(args.categoria))
