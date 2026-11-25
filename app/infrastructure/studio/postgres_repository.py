"""Repositórios do estúdio no Postgres (`asyncpg`). Colunas em português."""

from __future__ import annotations

from typing import Any, Protocol

from app.domain.studio.entities import NewVideoRequest, Reel, VideoRequest
from app.domain.studio.repository import ReelRepository, VideoRequestRepository


class AsyncPool(Protocol):
    async def execute(self, query: str, *args: object) -> str: ...
    async def fetch(self, query: str, *args: object) -> list[Any]: ...
    async def fetchrow(self, query: str, *args: object) -> Any: ...
    async def fetchval(self, query: str, *args: object) -> Any: ...


_REEL_COLUMNS = {
    "title": "titulo",
    "caption": "legenda",
    "theme": "tema",
    "published": "publicado",
}
_REQUEST_COLUMNS = {
    "status": "status",
    "stage": "etapa",
    "progress": "progresso",
    "error": "erro",
    "slug": "slug",
    "script": "roteiro",
    "voice_url": "voz_url",
}


def _reel(row: Any) -> Reel:
    return Reel(
        slug=row["slug"],
        title=row["titulo"],
        caption=row["legenda"],
        theme=row["tema"],
        width=row["largura"],
        height=row["altura"],
        video_url=row["video_url"],
        cover_url=row["capa_url"],
        published=row["publicado"],
        created_at=row["criado_em"],
    )


def _request(row: Any) -> VideoRequest:
    return VideoRequest(
        id=row["id"],
        theme=row["tema"],
        question=row["pergunta"],
        notes=row["notas"],
        format=row["formato"],
        status=row["status"],
        stage=row["etapa"],
        progress=row["progresso"],
        error=row["erro"],
        slug=row["slug"],
        own_voice=row["voz_propria"],
        script=row["roteiro"],
        voice_url=row["voz_url"],
        created_at=row["criado_em"],
        updated_at=row["atualizado_em"],
    )


async def create_schema(pool: AsyncPool) -> None:
    await pool.execute(
        """
        CREATE TABLE IF NOT EXISTS reels (
            slug TEXT PRIMARY KEY,
            titulo TEXT NOT NULL,
            legenda TEXT NOT NULL DEFAULT '',
            tema TEXT NOT NULL,
            largura INT NOT NULL,
            altura INT NOT NULL,
            video_url TEXT NOT NULL,
            capa_url TEXT NOT NULL,
            publicado BOOLEAN NOT NULL DEFAULT FALSE,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
            atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_reels_publicado_criado ON reels (publicado, criado_em DESC);
        CREATE TABLE IF NOT EXISTS pedidos_video (
            id BIGSERIAL PRIMARY KEY,
            tema TEXT NOT NULL,
            pergunta TEXT NOT NULL DEFAULT '',
            notas TEXT NOT NULL DEFAULT '',
            formato TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'na_fila',
            etapa TEXT NOT NULL DEFAULT '',
            progresso INT NOT NULL DEFAULT 0,
            erro TEXT NOT NULL DEFAULT '',
            slug TEXT,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
            atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_pedidos_video_status ON pedidos_video (status, id);
        ALTER TABLE pedidos_video ADD COLUMN IF NOT EXISTS voz_propria BOOLEAN NOT NULL DEFAULT FALSE;
        ALTER TABLE pedidos_video ADD COLUMN IF NOT EXISTS roteiro TEXT NOT NULL DEFAULT '';
        ALTER TABLE pedidos_video ADD COLUMN IF NOT EXISTS voz_url TEXT;
        """
    )


class PostgresReelRepository(ReelRepository):
    def __init__(self, pool: AsyncPool) -> None:
        self._pool = pool

    async def list(
        self, *, theme: str | None, only_published: bool, limit: int, offset: int
    ) -> tuple[list[Reel], int]:
        where = "WHERE ($1::text IS NULL OR tema = $1) AND (NOT $2 OR publicado)"
        rows = await self._pool.fetch(
            f"SELECT * FROM reels {where} ORDER BY criado_em DESC, slug DESC LIMIT $3 OFFSET $4",  # noqa: S608
            theme,
            only_published,
            limit,
            offset,
        )
        # `where` é texto fixo deste arquivo; os valores vão como parâmetros.
        count_sql = f"SELECT count(*) FROM reels {where}"  # noqa: S608
        total = await self._pool.fetchval(count_sql, theme, only_published)
        return [_reel(r) for r in rows], int(total)

    async def get(self, slug: str) -> Reel | None:
        row = await self._pool.fetchrow("SELECT * FROM reels WHERE slug = $1", slug)
        return _reel(row) if row else None

    async def create(self, reel: Reel) -> Reel:
        row = await self._pool.fetchrow(
            """
            INSERT INTO reels (slug, titulo, legenda, tema, largura, altura, video_url, capa_url, publicado, criado_em)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, coalesce($10, now()))
            ON CONFLICT (slug) DO NOTHING
            RETURNING *
            """,
            reel.slug,
            reel.title,
            reel.caption,
            reel.theme,
            reel.width,
            reel.height,
            reel.video_url,
            reel.cover_url,
            reel.published,
            reel.created_at,
        )
        if row is None:
            raise KeyError(reel.slug)
        return _reel(row)

    async def update(self, slug: str, patch: dict[str, object]) -> Reel | None:
        sets = ", ".join(
            f"{_REEL_COLUMNS[k]} = ${i}" for i, k in enumerate(patch, start=2)
        )
        row = await self._pool.fetchrow(
            f"UPDATE reels SET {sets}, atualizado_em = now() WHERE slug = $1 RETURNING *",  # noqa: S608
            slug,
            *patch.values(),
        )
        return _reel(row) if row else None

    async def delete(self, slug: str) -> bool:
        return (
            await self._pool.execute("DELETE FROM reels WHERE slug = $1", slug)
            == "DELETE 1"
        )


class PostgresVideoRequestRepository(VideoRequestRepository):
    def __init__(self, pool: AsyncPool) -> None:
        self._pool = pool

    async def create(self, request: NewVideoRequest) -> VideoRequest:
        row = await self._pool.fetchrow(
            "INSERT INTO pedidos_video (tema, pergunta, notas, formato, voz_propria)"
            " VALUES ($1, $2, $3, $4, $5) RETURNING *",
            request.theme,
            request.question,
            request.notes,
            request.format,
            request.own_voice,
        )
        return _request(row)

    async def list_recent(self, limit: int) -> list[VideoRequest]:
        rows = await self._pool.fetch(
            "SELECT * FROM pedidos_video ORDER BY id DESC LIMIT $1", limit
        )
        return [_request(r) for r in rows]

    async def get(self, request_id: int) -> VideoRequest | None:
        row = await self._pool.fetchrow(
            "SELECT * FROM pedidos_video WHERE id = $1", request_id
        )
        return _request(row) if row else None

    async def claim_next(self) -> VideoRequest | None:
        # SKIP LOCKED: dois geradores ao mesmo tempo nunca pegam o mesmo pedido.
        row = await self._pool.fetchrow(
            """
            UPDATE pedidos_video SET status = 'gerando', etapa = 'Começando', progresso = 0,
                   atualizado_em = now()
            WHERE id = (
                SELECT id FROM pedidos_video WHERE status = 'na_fila'
                ORDER BY id LIMIT 1 FOR UPDATE SKIP LOCKED
            )
            RETURNING *
            """
        )
        return _request(row) if row else None

    async def update(self, request_id: int, **fields: object) -> VideoRequest | None:
        sets = ", ".join(
            f"{_REQUEST_COLUMNS[k]} = ${i}" for i, k in enumerate(fields, start=2)
        )
        row = await self._pool.fetchrow(
            f"UPDATE pedidos_video SET {sets}, atualizado_em = now() WHERE id = $1 RETURNING *",  # noqa: S608
            request_id,
            *fields.values(),
        )
        return _request(row) if row else None
