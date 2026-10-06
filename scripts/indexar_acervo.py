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

Lote agrupa chunks de vários verbetes numa única chamada à Voyage (a maioria
dos verbetes tem só ~3 chunks — sem isso seriam ~1.750 chamadas). Entre
chamadas, `REQUEST_INTERVAL_SECONDS` respeita o limite de contas sem cartão
cadastrado na Voyage (3 requisições/minuto e 10K tokens/minuto); com cartão
cadastrado esse limite sobe bastante e o intervalo pode ser reduzido ou
removido. Mesmo respeitando o intervalo, o teto de tokens/minuto pode
estourar num lote com parágrafos longos — nesse caso `_RateLimitedEmbedder`
espera e tenta de novo o mesmo lote em vez de derrubar a indexação inteira.

A rodada inteira leva dezenas de minutos numa conta sem cartão, tempo
suficiente pra um blip de rede derrubar a conexão do pool com o Postgres no
meio de uma escrita — `_gravar_com_retentativas` reabre e tenta de novo em
vez de derrubar a indexação inteira por causa disso.
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
from app.domain.chat.exceptions import EmbeddingGenerationError
from app.infrastructure.acervo.json_repository import repository
from app.infrastructure.chat.postgres_repository import PostgresRagRepository
from app.infrastructure.chat.voyage_embedding_gateway import VoyageEmbeddingGateway
from app.models import AnyEntry

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("indexar_acervo")

# Tamanho de lote por chamada — a maioria dos verbetes tem só ~3 chunks, então
# um lote agrupa vários verbetes até esse teto. Reduzido de 40 pra 25 depois
# de bater no teto de 10K tokens/minuto com lotes que caíram em parágrafos
# longos (ex.: Catecismo) mesmo abaixo do teto de itens.
BATCH_SIZE = 25

# Intervalo mínimo entre chamadas à Voyage — respeita o teto de 3
# requisições/minuto de uma conta sem cartão cadastrado (20s seria o mínimo
# exato; a folga evita bater no limite por variação de latência).
REQUEST_INTERVAL_SECONDS = 21.0

# Quantas vezes tenta de novo o mesmo lote depois de um rate limit, e quanto
# espera entre tentativas — a Voyage não expõe o tempo exato até resetar a
# janela de 1 minuto, então a espera é generosa (mais que os 60s da janela).
RATE_LIMIT_RETRIES = 6
RATE_LIMIT_BACKOFF_SECONDS = 65.0

# Retentativa pra queda de conexão com o Postgres (blip de rede) — o pool
# abre uma conexão nova sozinho na próxima `acquire()`, só precisa tentar de
# novo a escrita que caiu no meio.
DB_RETRIES = 3
DB_BACKOFF_SECONDS = 5.0


class _RateLimitedEmbedder:
    """Encapsula `embed_documents` com intervalo mínimo entre chamadas e
    retentativa (não aborta a indexação inteira) quando bate rate limit."""

    def __init__(self, gateway: VoyageEmbeddingGateway, interval_seconds: float) -> None:
        self._gateway = gateway
        self._interval = interval_seconds
        self._last_call: float | None = None

    async def embed(self, textos: list[str]) -> list[list[float]]:
        for tentativa in range(1, RATE_LIMIT_RETRIES + 1):
            if self._last_call is not None:
                espera = self._interval - (asyncio.get_event_loop().time() - self._last_call)
                if espera > 0:
                    await asyncio.sleep(espera)
            try:
                resultado = await self._gateway.embed_documents(textos)
            except EmbeddingGenerationError:
                self._last_call = asyncio.get_event_loop().time()
                if tentativa == RATE_LIMIT_RETRIES:
                    raise
                logger.warning(
                    "Rate limit da Voyage — esperando %ds antes de tentar de novo (%d/%d)",
                    RATE_LIMIT_BACKOFF_SECONDS,
                    tentativa,
                    RATE_LIMIT_RETRIES,
                )
                await asyncio.sleep(RATE_LIMIT_BACKOFF_SECONDS)
            else:
                self._last_call = asyncio.get_event_loop().time()
                return resultado
        raise AssertionError("inalcançável — o loop sempre retorna ou levanta")


async def _gravar_com_retentativas(
    repo: PostgresRagRepository,
    chunks: list[ChunkInput],
    embeddings: list[list[float]],
) -> None:
    for tentativa in range(1, DB_RETRIES + 1):
        try:
            await repo.replace_source(chunks[0].source_type, chunks[0].source_ref, chunks, embeddings)
            return
        except (OSError, asyncpg.PostgresConnectionError, asyncpg.InterfaceError):
            if tentativa == DB_RETRIES:
                raise
            logger.warning(
                "Conexão com o Postgres caiu — tentando de novo em %ds (%d/%d)",
                DB_BACKOFF_SECONDS,
                tentativa,
                DB_RETRIES,
            )
            await asyncio.sleep(DB_BACKOFF_SECONDS)


async def _indexar_lote(
    repo: PostgresRagRepository,
    embedder: _RateLimitedEmbedder,
    lote: list[tuple[AnyEntry, list[ChunkInput]]],
) -> None:
    """Gera embedding de um lote (chunks de um ou mais verbetes) numa chamada
    só e grava cada verbete separadamente (`replace_source` é por verbete)."""
    todos_chunks = [chunk for _entry, chunks in lote for chunk in chunks]
    if not todos_chunks:
        return
    embeddings = await embedder.embed([chunk.text for chunk in todos_chunks])

    cursor = 0
    for _entry, chunks in lote:
        fatia = embeddings[cursor : cursor + len(chunks)]
        cursor += len(chunks)
        await _gravar_com_retentativas(repo, chunks, fatia)


async def main(categoria_filtro: str | None, continuar: bool) -> None:
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

    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=5)
    try:
        await PostgresRagRepository.create_schema(pool)
        repo = PostgresRagRepository(pool)
        embedder = _RateLimitedEmbedder(VoyageEmbeddingGateway(), REQUEST_INTERVAL_SECONDS)

        if continuar:
            linhas = await pool.fetch(
                "SELECT DISTINCT fonte_ref FROM rag_chunks WHERE fonte_tipo = 'acervo'"
            )
            ja_indexados = {row["fonte_ref"] for row in linhas}
            antes = len(entradas)
            entradas = [
                e for e in entradas if f"{e.categoria.value}/{e.slug}" not in ja_indexados
            ]
            logger.info(
                "--continuar: %d de %d verbetes já indexados, pulando.",
                antes - len(entradas),
                antes,
            )

        logger.info("Indexando %d entradas...", len(entradas))

        total_chunks = 0
        entradas_processadas = 0
        lote: list[tuple[AnyEntry, list[ChunkInput]]] = []
        tamanho_lote = 0
        for entry in entradas:
            chunks = chunk_entry(entry)
            if lote and tamanho_lote + len(chunks) > BATCH_SIZE:
                await _indexar_lote(repo, embedder, lote)
                entradas_processadas += len(lote)
                logger.info(
                    "  %d/%d verbetes (%d chunks até aqui)",
                    entradas_processadas,
                    len(entradas),
                    total_chunks,
                )
                lote = []
                tamanho_lote = 0
            lote.append((entry, chunks))
            tamanho_lote += len(chunks)
            total_chunks += len(chunks)
        if lote:
            await _indexar_lote(repo, embedder, lote)
            entradas_processadas += len(lote)
            logger.info(
                "  %d/%d verbetes (%d chunks até aqui)",
                entradas_processadas,
                len(entradas),
                total_chunks,
            )
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
    parser.add_argument(
        "--continuar",
        action="store_true",
        help=(
            "Pula verbetes já indexados em vez de reindexar tudo — útil pra retomar "
            "depois de uma queda no meio da indexação completa. Não reindexa verbetes "
            "cujo conteúdo mudou desde a última vez; rode sem esta flag pra isso."
        ),
    )
    args = parser.parse_args()
    asyncio.run(main(args.categoria, args.continuar))
