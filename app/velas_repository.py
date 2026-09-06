"""Acesso a dados do mural de velas.

Duas implementações atrás da mesma interface: `PostgresVelasRepository`,
usada em produção, e `InMemoryVelasRepository`, usada nos testes — nenhum
teste precisa de um Postgres de verdade rodando. `get_velas_repository` é o
único ponto que decide qual delas está ativa (`app.state.velas_repository`,
setado no lifespan do `main.py`).
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Protocol

from fastapi import Request

from app.exceptions import RateLimitedException, ServiceUnavailableException
from app.velas_models import TipoVela, Vela, VelaCreate

logger = logging.getLogger(__name__)

# Uma vela por IP a cada N segundos — só para conter flood grosseiro de bot,
# não é uma defesa séria contra abuso coordenado. Em memória porque um
# processo só (Render free) não precisa de Redis para isto.
RATE_LIMIT_SECONDS = 20.0


class AsyncPool(Protocol):
    """O subconjunto de `asyncpg.Pool` que este módulo usa — só para tipar."""

    async def execute(self, query: str, *args: object) -> str: ...
    async def fetchrow(self, query: str, *args: object) -> object | None: ...
    async def fetch(self, query: str, *args: object) -> list[object]: ...
    async def fetchval(self, query: str, *args: object) -> object: ...


class VelasRepository(ABC):
    """Interface que o router depende — implementação é um detalhe."""

    @abstractmethod
    async def create(self, payload: VelaCreate) -> Vela: ...

    @abstractmethod
    async def list_page(self, limit: int, offset: int) -> tuple[list[Vela], int]: ...


class RateLimiter:
    """Guarda o horário do último acender por IP, em memória do processo."""

    def __init__(self, window_seconds: float = RATE_LIMIT_SECONDS) -> None:
        self._window = window_seconds
        self._last_seen: dict[str, float] = {}

    def check(self, client_ip: str) -> None:
        now = time.monotonic()
        last = self._last_seen.get(client_ip)
        if last is not None and (now - last) < self._window:
            wait = round(self._window - (now - last))
            raise RateLimitedException(
                message=f"Espere {wait}s antes de acender outra vela.",
                details={"retry_after_seconds": wait},
            )
        self._last_seen[client_ip] = now


def client_ip(request: Request) -> str:
    """IP do cliente, respeitando o proxy do Render (`X-Forwarded-For`)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "desconhecido"


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

    async def create(self, payload: VelaCreate) -> Vela:
        # `email` é gravado mas fica fora do RETURNING de propósito: nunca
        # deve voltar como um `Vela` (contato privado, não campo público).
        row = await self._pool.fetchrow(
            """
            INSERT INTO velas (nome, intencao, tipo, cidade, estado, email)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id, nome, intencao, tipo, cidade, estado, criado_em
            """,
            payload.nome,
            payload.intencao,
            payload.tipo.value,
            payload.cidade,
            payload.estado,
            payload.email,
        )
        assert row is not None  # noqa: S101 — INSERT ... RETURNING sempre devolve 1 linha
        return Vela(**dict(row))

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
        itens = [Vela(**dict(row)) for row in rows]
        return itens, int(total)


class InMemoryVelasRepository(VelasRepository):
    """Fake usada nos testes — mesma interface, sem rede nem Postgres."""

    def __init__(self) -> None:
        self._itens: list[Vela] = []
        self._next_id = 1

    async def create(self, payload: VelaCreate) -> Vela:
        vela = Vela(
            id=self._next_id,
            nome=payload.nome,
            intencao=payload.intencao,
            tipo=payload.tipo,
            cidade=payload.cidade,
            estado=payload.estado,
            criado_em=datetime.now(UTC),
        )
        self._itens.insert(0, vela)
        self._next_id += 1
        return vela

    async def list_page(self, limit: int, offset: int) -> tuple[list[Vela], int]:
        total = len(self._itens)
        return self._itens[offset : offset + limit], total


def require_repository(repo: VelasRepository | None) -> VelasRepository:
    """Traduz "banco não configurado" em 503, não em 500 nem crash de boot."""
    if repo is None:
        raise ServiceUnavailableException(
            message="O mural de velas está temporariamente indisponível.",
            code="VELAS_INDISPONIVEL",
        )
    return repo


__all__ = [
    "TipoVela",
    "Vela",
    "VelaCreate",
    "VelasRepository",
    "PostgresVelasRepository",
    "InMemoryVelasRepository",
    "RateLimiter",
    "client_ip",
    "require_repository",
]
