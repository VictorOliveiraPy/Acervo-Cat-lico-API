"""Implementação de produção do repositório de perfis, sobre `asyncpg`.

Os pontos não têm coluna: são calculados das lições concluídas, para nunca
divergirem delas. Colunas em português, como as demais tabelas do projeto.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Protocol

from app.domain.profiles.entities import (
    MAX_ITEMS_PER_USER,
    POINTS_PER_LESSON,
    ActivityId,
    Favorite,
    Note,
    PatronSaint,
    Profile,
    RankingRow,
)
from app.domain.profiles.repository import ProfileRepository


class AsyncPool(Protocol):
    """O subconjunto de `asyncpg.Pool` que este módulo usa — só para tipar."""

    async def execute(self, query: str, *args: object) -> str: ...
    async def fetchrow(self, query: str, *args: object) -> Any: ...
    async def fetch(self, query: str, *args: object) -> list[Any]: ...


def _favorite(row: Any) -> Favorite:
    return Favorite(
        row["id"],
        row["tipo"],
        row["texto"],
        row["referencia"],
        row["url_origem"],
        row["criado_em"],
    )


def _note(row: Any) -> Note:
    return Note(
        row["id"],
        row["categoria"],
        row["texto"],
        row["licao"],
        row["criado_em"],
        row["atualizado_em"],
    )


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
            ALTER TABLE perfis
                ADD COLUMN IF NOT EXISTS padroeiro_id TEXT;
            -- Perfil novo fica sem padroeiro até a pessoa escolher; os antigos mantêm o seu.
            ALTER TABLE perfis ALTER COLUMN padroeiro_id DROP NOT NULL;
            ALTER TABLE perfis ALTER COLUMN padroeiro_id DROP DEFAULT;
            -- Uma linha por prática e dia: marcar de novo no mesmo dia não duplica.
            -- `pontos` guarda o que valia na hora, para mudar a tabela sem mexer no passado.
            -- Dia de Brasília da conclusão, para a sequência de dias; as antigas
            -- herdam o dia de `concluida_em`.
            ALTER TABLE perfil_licoes ADD COLUMN IF NOT EXISTS dia DATE;
            UPDATE perfil_licoes
                SET dia = (concluida_em AT TIME ZONE 'America/Sao_Paulo')::date
                WHERE dia IS NULL;
            CREATE TABLE IF NOT EXISTS perfil_atividades (
                google_sub TEXT NOT NULL REFERENCES perfis (google_sub) ON DELETE CASCADE,
                atividade TEXT NOT NULL,
                dia DATE NOT NULL,
                pontos INT NOT NULL,
                PRIMARY KEY (google_sub, atividade, dia)
            );
            CREATE TABLE IF NOT EXISTS perfil_caminho (
                google_sub TEXT NOT NULL REFERENCES perfis (google_sub) ON DELETE CASCADE,
                casa INT NOT NULL,
                dia DATE NOT NULL,
                PRIMARY KEY (google_sub, casa)
            );
            CREATE TABLE IF NOT EXISTS favoritos (
                id BIGSERIAL PRIMARY KEY,
                google_sub TEXT NOT NULL REFERENCES perfis (google_sub) ON DELETE CASCADE,
                tipo TEXT NOT NULL,
                texto TEXT NOT NULL,
                referencia TEXT NOT NULL DEFAULT '',
                url_origem TEXT,
                criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            CREATE INDEX IF NOT EXISTS favoritos_google_sub_idx
                ON favoritos (google_sub, criado_em DESC);
            CREATE TABLE IF NOT EXISTS anotacoes (
                id BIGSERIAL PRIMARY KEY,
                google_sub TEXT NOT NULL REFERENCES perfis (google_sub) ON DELETE CASCADE,
                categoria TEXT NOT NULL,
                texto TEXT NOT NULL,
                licao TEXT,
                criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
                atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            CREATE INDEX IF NOT EXISTS anotacoes_google_sub_idx
                ON anotacoes (google_sub, criado_em DESC);
            """
        )

    async def _load(self, subject: str) -> Profile | None:
        row = await self._pool.fetchrow(
            """
            SELECT nome_exibicao, preferencias, no_ranking, padroeiro_id
            FROM perfis WHERE google_sub = $1
            """,
            subject,
        )
        if row is None:
            return None
        lessons = await self._pool.fetch(
            "SELECT licao, dia FROM perfil_licoes WHERE google_sub = $1 ORDER BY concluida_em",
            subject,
        )
        activity_days = await self._pool.fetch(
            "SELECT DISTINCT dia FROM perfil_atividades WHERE google_sub = $1",
            subject,
        )
        slugs = [lesson["licao"] for lesson in lessons]
        activities = await self._pool.fetch(
            """
            SELECT atividade, max(dia) AS ultimo_dia, sum(pontos)::int AS pontos
            FROM perfil_atividades WHERE google_sub = $1
            GROUP BY atividade
            """,
            subject,
        )
        path = await self._pool.fetch(
            "SELECT casa, dia FROM perfil_caminho WHERE google_sub = $1 ORDER BY casa",
            subject,
        )
        return Profile(
            display_name=row["nome_exibicao"],
            preferences=list(row["preferencias"]),
            show_in_ranking=row["no_ranking"],
            points=len(slugs) * POINTS_PER_LESSON + sum(a["pontos"] for a in activities),
            completed_lessons=slugs,
            patron_saint=row["padroeiro_id"],
            last_activity_days={a["atividade"]: a["ultimo_dia"] for a in activities},
            active_days=frozenset(lesson["dia"] for lesson in lessons if lesson["dia"])
            | frozenset(a["dia"] for a in activity_days),
            path_steps=tuple((step["casa"], step["dia"]) for step in path),
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

    async def exists(self, subject: str) -> bool:
        row = await self._pool.fetchrow("SELECT 1 FROM perfis WHERE google_sub = $1", subject)
        return row is not None

    async def get(self, subject: str) -> Profile | None:
        return await self._load(subject)

    async def set_patron(self, subject: str, patron_saint: PatronSaint) -> Profile | None:
        await self._pool.execute(
            "UPDATE perfis SET padroeiro_id = $2 WHERE google_sub = $1",
            subject,
            patron_saint,
        )
        return await self._load(subject)

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

    async def complete_lessons(
        self, subject: str, lessons: list[str], day: date
    ) -> Profile | None:
        if not await self.exists(subject):
            return None
        await self._pool.execute(
            """
            INSERT INTO perfil_licoes (google_sub, licao, dia)
            SELECT $1, unnest($2::text[]), $3
            ON CONFLICT (google_sub, licao) DO NOTHING
            """,
            subject,
            lessons,
            day,
        )
        return await self._load(subject)

    async def complete_activity(
        self, subject: str, activity: ActivityId, day: date, points: int
    ) -> Profile | None:
        if not await self.exists(subject):
            return None
        await self._pool.execute(
            """
            INSERT INTO perfil_atividades (google_sub, atividade, dia, pontos)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (google_sub, atividade, dia) DO NOTHING
            """,
            subject,
            activity,
            day,
            points,
        )
        return await self._load(subject)

    async def advance_path(self, subject: str, house: int, day: date) -> Profile | None:
        if not await self.exists(subject):
            return None
        await self._pool.execute(
            """
            INSERT INTO perfil_caminho (google_sub, casa, dia) VALUES ($1, $2, $3)
            ON CONFLICT (google_sub, casa) DO NOTHING
            """,
            subject,
            house,
            day,
        )
        return await self._load(subject)

    async def delete(self, subject: str) -> None:
        await self._pool.execute("DELETE FROM perfis WHERE google_sub = $1", subject)

    async def ranking(self, limit: int) -> list[RankingRow]:
        rows = await self._pool.fetch(
            """
            SELECT nome_exibicao, pontos FROM (
                SELECT
                    p.nome_exibicao,
                    (SELECT count(*) FROM perfil_licoes l WHERE l.google_sub = p.google_sub)
                        * $2::int
                    + (SELECT coalesce(sum(a.pontos), 0) FROM perfil_atividades a
                       WHERE a.google_sub = p.google_sub)::int AS pontos
                FROM perfis p
                WHERE p.no_ranking
            ) pontuados
            WHERE pontos > 0
            ORDER BY pontos DESC, nome_exibicao
            LIMIT $1
            """,
            limit,
            POINTS_PER_LESSON,
        )
        return [RankingRow(row["nome_exibicao"], row["pontos"]) for row in rows]

    # Toda consulta abaixo filtra por `google_sub`: é o que impede uma pessoa de ler
    # ou apagar o que é de outra, mesmo informando um `id` válido.

    async def list_favorites(self, subject: str) -> list[Favorite]:
        rows = await self._pool.fetch(
            """
            SELECT id, tipo, texto, referencia, url_origem, criado_em
            FROM favoritos WHERE google_sub = $1
            ORDER BY criado_em DESC, id DESC
            """,
            subject,
        )
        return [_favorite(row) for row in rows]

    async def add_favorite(
        self,
        subject: str,
        kind: str,
        text: str,
        reference: str,
        source_url: str | None,
    ) -> Favorite | None:
        row = await self._pool.fetchrow(
            """
            INSERT INTO favoritos (google_sub, tipo, texto, referencia, url_origem)
            SELECT $1, $2, $3, $4, $5
            WHERE (SELECT count(*) FROM favoritos WHERE google_sub = $1) < $6
            RETURNING id, tipo, texto, referencia, url_origem, criado_em
            """,
            subject,
            kind,
            text,
            reference,
            source_url,
            MAX_ITEMS_PER_USER,
        )
        return _favorite(row) if row else None

    async def delete_favorite(self, subject: str, favorite_id: int) -> bool:
        result = await self._pool.execute(
            "DELETE FROM favoritos WHERE id = $1 AND google_sub = $2", favorite_id, subject
        )
        return result == "DELETE 1"

    async def list_notes(self, subject: str) -> list[Note]:
        rows = await self._pool.fetch(
            """
            SELECT id, categoria, texto, licao, criado_em, atualizado_em
            FROM anotacoes WHERE google_sub = $1
            ORDER BY criado_em DESC, id DESC
            """,
            subject,
        )
        return [_note(row) for row in rows]

    async def add_note(
        self,
        subject: str,
        tag: str,
        body: str,
        lesson: str | None,
    ) -> Note | None:
        row = await self._pool.fetchrow(
            """
            INSERT INTO anotacoes (google_sub, categoria, texto, licao)
            SELECT $1, $2, $3, $4
            WHERE (SELECT count(*) FROM anotacoes WHERE google_sub = $1) < $5
            RETURNING id, categoria, texto, licao, criado_em, atualizado_em
            """,
            subject,
            tag,
            body,
            lesson,
            MAX_ITEMS_PER_USER,
        )
        return _note(row) if row else None

    async def delete_note(self, subject: str, note_id: int) -> bool:
        result = await self._pool.execute(
            "DELETE FROM anotacoes WHERE id = $1 AND google_sub = $2", note_id, subject
        )
        return result == "DELETE 1"
