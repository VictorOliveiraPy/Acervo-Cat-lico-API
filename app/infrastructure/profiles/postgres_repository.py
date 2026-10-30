"""Implementação de produção do repositório de perfis, sobre `asyncpg`.

Os pontos não têm coluna: são calculados das lições concluídas, para nunca
divergirem delas. Colunas em português, como as demais tabelas do projeto.
"""

from __future__ import annotations

from typing import Any, Protocol

from app.domain.profiles.entities import POINTS_PER_LESSON, Profile, RankingRow
from app.domain.profiles.repository import ProfileRepository


class AsyncPool(Protocol):
    """O subconjunto de `asyncpg.Pool` que este módulo usa — só para tipar."""

    async def execute(self, query: str, *args: object) -> str: ...
    async def fetchrow(self, query: str, *args: object) -> Any: ...
    async def fetch(self, query: str, *args: object) -> list[Any]: ...


class PostgresProfileRepository(ProfileRepository):
    def __init__(self, pool: AsyncPool) -> None:
        self._pool = pool

    @staticmethod
    async def create_schema(pool: AsyncPool) -> None:
        await pool.execute(
            """
            CREATE TABLE IF NOT EXISTS perfis (
                google_sub TEXT PRIMARY KEY,
                nome_exibicao TEXT NOT NULL,
                preferencias TEXT[] NOT NULL DEFAULT '{}',
                no_ranking BOOLEAN NOT NULL DEFAULT FALSE,
                criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            CREATE TABLE IF NOT EXISTS perfil_licoes (
                google_sub TEXT NOT NULL REFERENCES perfis (google_sub) ON DELETE CASCADE,
                licao TEXT NOT NULL,
                concluida_em TIMESTAMPTZ NOT NULL DEFAULT now(),
                PRIMARY KEY (google_sub, licao)
            );
            """
        )

    async def _load(self, subject: str) -> Profile | None:
        row = await self._pool.fetchrow(
            "SELECT nome_exibicao, preferencias, no_ranking FROM perfis WHERE google_sub = $1",
            subject,
        )
        if row is None:
            return None
        lessons = await self._pool.fetch(
            "SELECT licao FROM perfil_licoes WHERE google_sub = $1 ORDER BY concluida_em",
            subject,
        )
        slugs = [lesson["licao"] for lesson in lessons]
        return Profile(
            display_name=row["nome_exibicao"],
            preferences=list(row["preferencias"]),
            show_in_ranking=row["no_ranking"],
            points=len(slugs) * POINTS_PER_LESSON,
            completed_lessons=slugs,
        )

    async def ensure(self, subject: str, display_name: str) -> Profile:
        await self._pool.execute(
            """
            INSERT INTO perfis (google_sub, nome_exibicao) VALUES ($1, $2)
            ON CONFLICT (google_sub) DO NOTHING
            """,
            subject,
            display_name,
        )
        profile = await self._load(subject)
        assert profile is not None  # noqa: S101 — acabou de ser garantido acima
        return profile

    async def update(
        self,
        subject: str,
        display_name: str,
        preferences: list[str],
        show_in_ranking: bool,
    ) -> Profile | None:
        await self._pool.execute(
            """
            UPDATE perfis SET nome_exibicao = $2, preferencias = $3, no_ranking = $4
            WHERE google_sub = $1
            """,
            subject,
            display_name,
            preferences,
            show_in_ranking,
        )
        return await self._load(subject)

    async def complete_lessons(self, subject: str, lessons: list[str]) -> Profile | None:
        if await self._load(subject) is None:
            return None
        await self._pool.execute(
            """
            INSERT INTO perfil_licoes (google_sub, licao)
            SELECT $1, unnest($2::text[])
            ON CONFLICT (google_sub, licao) DO NOTHING
            """,
            subject,
            lessons,
        )
        return await self._load(subject)

    async def delete(self, subject: str) -> None:
        await self._pool.execute("DELETE FROM perfis WHERE google_sub = $1", subject)

    async def ranking(self, limit: int) -> list[RankingRow]:
        rows = await self._pool.fetch(
            """
            SELECT p.nome_exibicao, count(l.licao) * $2::int AS pontos
            FROM perfis p
            JOIN perfil_licoes l ON l.google_sub = p.google_sub
            WHERE p.no_ranking
            GROUP BY p.google_sub, p.nome_exibicao
            ORDER BY pontos DESC, p.nome_exibicao
            LIMIT $1
            """,
            limit,
            POINTS_PER_LESSON,
        )
        return [RankingRow(row["nome_exibicao"], row["pontos"]) for row in rows]
