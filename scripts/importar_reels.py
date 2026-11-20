"""Leva os reels do site (lib/reels.json do front) para a tabela `reels` da API.

Roda uma vez, na migração; rodar de novo não duplica (pula o que já existe). Todos
entram publicados e na mesma ordem do JSON (o primeiro é o mais novo). O MP4 continua
no R2 e a capa continua servida pelo site (`/reels/<slug>.jpg`).

    python -m scripts.importar_reels ../Acervo-Cat-lico-Web/lib/reels.json
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import asyncpg

from app.core.config import settings
from app.domain.studio.rules import new_reel
from app.infrastructure.studio.postgres_repository import (
    PostgresReelRepository,
    create_schema,
)

INICIO = datetime(2026, 1, 1, tzinfo=UTC)


async def importar(caminho: Path) -> None:
    reels = json.loads(caminho.read_text(encoding="utf-8"))
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    await create_schema(pool)
    repo = PostgresReelRepository(pool)
    novos = 0
    for posicao, item in enumerate(reels):
        reel = new_reel(
            {
                "slug": item["slug"],
                "titulo": item["title"],
                "legenda": item["caption"],
                "tema": item["tema"],
                "largura": item["width"],
                "altura": item["height"],
                "video_url": f"{settings.r2_public_base_url}/reels/{item['slug']}.mp4",
                "capa_url": f"/reels/{item['slug']}.jpg",
                "publicado": True,
            }
        )
        # Datas em ordem decrescente: o primeiro do JSON fica como o mais recente.
        reel = reel.__class__(
            **{**reel.__dict__, "created_at": INICIO - timedelta(minutes=posicao)}
        )
        try:
            await repo.create(reel)
            novos += 1
        except KeyError:
            continue
    await pool.close()
    print(f"{novos} reels importados, {len(reels) - novos} já estavam lá.")


if __name__ == "__main__":
    asyncio.run(importar(Path(sys.argv[1])))
