"""Implementação de produção do repositório de velas, sobre `asyncpg`.

Colunas da tabela `velas` permanecem em português (`nome`, `tipo`,
`criado_em`...) — é schema de banco já em produção, sem motivo pra migrar;
o mapeamento para os nomes em inglês da entidade acontece só aqui.
"""

from __future__ import annotations

from typing import Any, Protocol

from app.domain.candles.entities import Candle, CandleType, NewCandle
from app.domain.candles.repository import CandleRepository


def _candle_from_row(row: object) -> Candle:
    """`Candle` é um dataclass simples, não um `BaseModel` — sem a coerção
    automática do Pydantic, `candle_type` chegaria do Postgres como `str`,
    não `CandleType`."""
    data = dict(row)  # type: ignore[call-overload]
    return Candle(
        id=data["id"],
        name=data["nome"],
        intention=data["intencao"],
        candle_type=CandleType(data["tipo"]),
        city=data["cidade"],
        state=data["estado"],
        created_at=data["criado_em"],
    )


class AsyncPool(Protocol):
    """O subconjunto de `asyncpg.Pool` que este módulo usa — só para tipar."""

    async def execute(self, query: str, *args: object) -> str: ...
    async def fetchrow(self, query: str, *args: object) -> object | None: ...
    async def fetch(self, query: str, *args: object) -> list[object]: ...
    async def fetchval(self, query: str, *args: object) -> Any: ...


class PostgresCandleRepository(CandleRepository):
    """Implementação de produção, sobre um pool `asyncpg`."""

    def __init__(self, pool: AsyncPool) -> None:
        self._pool = pool

    @staticmethod
    async def create_schema(pool: AsyncPool) -> None:
        """Cria a tabela se não existir, e adiciona colunas novas nela se já
        existir — `ADD COLUMN IF NOT EXISTS` é seguro de rodar toda subida,
        inclusive num banco com velas reais já gravadas (não trunca nada)."""
        await pool.execute(
            """
            CREATE TABLE IF NOT EXISTS velas (
                id BIGSERIAL PRIMARY KEY,
                nome TEXT NOT NULL,
                intencao TEXT,
                tipo TEXT NOT NULL,
                criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            CREATE INDEX IF NOT EXISTS idx_velas_criado_em
                ON velas (criado_em DESC);
            ALTER TABLE velas ADD COLUMN IF NOT EXISTS cidade TEXT;
            ALTER TABLE velas ADD COLUMN IF NOT EXISTS estado TEXT;
            ALTER TABLE velas ADD COLUMN IF NOT EXISTS email TEXT;
            """
        )

    async def create(self, new_candle: NewCandle) -> Candle:
        # `email` é gravado mas fica fora do RETURNING de propósito: nunca
        # deve voltar como uma `Candle` (contato privado, não campo público).
        row = await self._pool.fetchrow(
            """
            INSERT INTO velas (nome, intencao, tipo, cidade, estado, email)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id, nome, intencao, tipo, cidade, estado, criado_em
            """,
            new_candle.name,
            new_candle.intention,
            new_candle.candle_type.value,
            new_candle.city,
            new_candle.state,
            new_candle.email,
        )
        assert row is not None  # noqa: S101 — INSERT ... RETURNING sempre devolve 1 linha
        return _candle_from_row(row)

    async def list_page(self, limit: int, offset: int) -> tuple[list[Candle], int]:
        total = await self._pool.fetchval("SELECT count(*) FROM velas")
        rows = await self._pool.fetch(
            """
            SELECT id, nome, intencao, tipo, cidade, estado, criado_em
            FROM velas
            ORDER BY criado_em DESC
            LIMIT $1 OFFSET $2
            """,
            limit,
            offset,
        )
        items = [_candle_from_row(row) for row in rows]
        return items, int(total)
