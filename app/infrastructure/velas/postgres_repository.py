"""Implementação de produção do repositório de velas, sobre `asyncpg`."""

from __future__ import annotations

from typing import Any, Protocol

from app.domain.velas.entities import NovaVela, TipoVela, Vela
from app.domain.velas.repository import VelasRepository


def _vela_from_row(row: object) -> Vela:
    """`Vela` é um dataclass simples, não um `BaseModel` — sem a coerção
    automática do Pydantic, `tipo` chegaria do Postgres como `str`, não
    `TipoVela`."""
    data = dict(row)  # type: ignore[call-overload]
    data["tipo"] = TipoVela(data["tipo"])
    return Vela(**data)


class AsyncPool(Protocol):
    """O subconjunto de `asyncpg.Pool` que este módulo usa — só para tipar."""

    async def execute(self, query: str, *args: object) -> str: ...
    async def fetchrow(self, query: str, *args: object) -> object | None: ...
    async def fetch(self, query: str, *args: object) -> list[object]: ...
    async def fetchval(self, query: str, *args: object) -> Any: ...


class PostgresVelasRepository(VelasRepository):
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

    async def create(self, nova_vela: NovaVela) -> Vela:
        # `email` é gravado mas fica fora do RETURNING de propósito: nunca
        # deve voltar como uma `Vela` (contato privado, não campo público).
        row = await self._pool.fetchrow(
            """
            INSERT INTO velas (nome, intencao, tipo, cidade, estado, email)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id, nome, intencao, tipo, cidade, estado, criado_em
            """,
            nova_vela.nome,
            nova_vela.intencao,
            nova_vela.tipo.value,
            nova_vela.cidade,
            nova_vela.estado,
            nova_vela.email,
        )
        assert row is not None  # noqa: S101 — INSERT ... RETURNING sempre devolve 1 linha
        return _vela_from_row(row)

    async def list_page(self, limit: int, offset: int) -> tuple[list[Vela], int]:
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
        itens = [_vela_from_row(row) for row in rows]
        return itens, int(total)
