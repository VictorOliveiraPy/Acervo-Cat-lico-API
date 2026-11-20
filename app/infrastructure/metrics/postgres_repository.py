"""Métricas de visitas no Postgres (`asyncpg`). Colunas em português, como as outras tabelas."""

from __future__ import annotations

from datetime import date
from typing import Any, Protocol

from app.domain.metrics.entities import DayCount, NewHit, Ranked
from app.domain.metrics.repository import MetricsRepository

# Coluna de cada ranking e o tipo de linha que ele conta. Lista fechada: o nome da
# coluna entra no SQL, então nunca vem de fora.
_RANKINGS: dict[str, tuple[str, str]] = {
    "caminho": ("caminho", "pagina"),
    "origem": ("origem", "pagina"),
    "dispositivo": ("dispositivo", "pagina"),
    "evento": ("evento", "evento"),
}

# Guardamos pouco mais de um ano: dá para comparar com o mesmo mês do ano anterior.
RETENTION_DAYS = 400


class AsyncPool(Protocol):
    async def execute(self, query: str, *args: object) -> str: ...
    async def fetch(self, query: str, *args: object) -> list[Any]: ...
    async def fetchrow(self, query: str, *args: object) -> Any: ...


class PostgresMetricsRepository(MetricsRepository):
    def __init__(self, pool: AsyncPool) -> None:
        self._pool = pool

    @staticmethod
    async def create_schema(pool: AsyncPool) -> None:
        """Cria a tabela se faltar e apaga o que passou da retenção (roda a cada subida)."""
        await pool.execute(
            """
            CREATE TABLE IF NOT EXISTS metricas (
                id BIGSERIAL PRIMARY KEY,
                dia DATE NOT NULL,
                tipo TEXT NOT NULL,
                caminho TEXT NOT NULL,
                evento TEXT,
                origem TEXT,
                dispositivo TEXT NOT NULL,
                visitante TEXT NOT NULL,
                criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            CREATE INDEX IF NOT EXISTS idx_metricas_dia_tipo ON metricas (dia, tipo);
            """
        )
        await pool.execute(
            "DELETE FROM metricas WHERE dia < CURRENT_DATE - $1::int", RETENTION_DAYS
        )

    async def record(self, hit: NewHit) -> None:
        await self._pool.execute(
            """
            INSERT INTO metricas (dia, tipo, caminho, evento, origem, dispositivo, visitante)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            hit.day,
            hit.kind,
            hit.path,
            hit.event,
            hit.referrer,
            hit.device,
            hit.visitor,
        )

    async def daily(self, start: date, end: date) -> list[DayCount]:
        rows = await self._pool.fetch(
            """
            SELECT dia, count(DISTINCT visitante) AS visitantes,
                   count(*) FILTER (WHERE tipo = 'pagina') AS paginas
            FROM metricas WHERE dia BETWEEN $1 AND $2
            GROUP BY dia ORDER BY dia
            """,
            start,
            end,
        )
        return [
            DayCount(day=r["dia"], visitors=r["visitantes"], views=r["paginas"])
            for r in rows
        ]

    async def totals(self, start: date, end: date) -> tuple[int, int]:
        row = await self._pool.fetchrow(
            """
            SELECT count(DISTINCT (dia, visitante)) AS visitantes,
                   count(*) FILTER (WHERE tipo = 'pagina') AS paginas
            FROM metricas WHERE dia BETWEEN $1 AND $2
            """,
            start,
            end,
        )
        return int(row["visitantes"]), int(row["paginas"])

    async def top(self, start: date, end: date, field: str, limit: int) -> list[Ranked]:
        column, kind = _RANKINGS[field]
        rows = await self._pool.fetch(
            f"""
            SELECT {column} AS nome, count(*) AS total
            FROM metricas
            WHERE dia BETWEEN $1 AND $2 AND tipo = $3 AND {column} IS NOT NULL
            GROUP BY {column} ORDER BY total DESC, nome LIMIT $4
            """,  # noqa: S608 — `column` vem de `_RANKINGS`, nunca de fora.
            start,
            end,
            kind,
            limit,
        )
        return [Ranked(name=r["nome"], count=r["total"]) for r in rows]
