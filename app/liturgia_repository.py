"""Acesso e cache da liturgia diária.

A fonte externa (`liturgia_client.fetch_liturgia`) é buscada no máximo uma
vez por dia: a primeira requisição do dia busca e grava; as seguintes leem
do cache. Isso protege o site de dois problemas do agregador de terceiros —
lentidão e instabilidade — sem nunca depender dele em tempo real depois da
primeira leitura do dia.

Mesmo padrão de duas implementações de `velas_repository.py`:
`PostgresLiturgiaDiariaRepository` em produção, `InMemoryLiturgiaDiariaRepository`
nos testes — nenhum teste depende de rede nem de Postgres de verdade.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from datetime import date
from typing import Protocol

from app.exceptions import ServiceUnavailableException
from app.liturgia_client import fetch_liturgia
from app.liturgia_models import LiturgiaDiaria

logger = logging.getLogger(__name__)

Fetcher = Callable[[date], Awaitable[LiturgiaDiaria]]


class AsyncPool(Protocol):
    """O subconjunto de `asyncpg.Pool` que este módulo usa — só para tipar."""

    async def execute(self, query: str, *args: object) -> str: ...
    async def fetchrow(self, query: str, *args: object) -> object | None: ...


class LiturgiaDiariaRepository(ABC):
    """Interface que a rota depende — implementação é um detalhe."""

    @abstractmethod
    async def get(self, dia: date) -> LiturgiaDiaria: ...


def _buscar_ou_falhar(fetcher: Fetcher) -> Fetcher:
    """Envolve o fetcher pra virar `ServiceUnavailableException` em vez de
    deixar o erro da fonte externa (timeout, HTTP 5xx, JSON malformado)
    vazar como 500 cru pro cliente."""

    async def wrapped(dia: date) -> LiturgiaDiaria:
        try:
            return await fetcher(dia)
        except Exception as exc:
            logger.warning("Falha ao buscar liturgia de %s: %s", dia, exc)
            raise ServiceUnavailableException(
                message="Não foi possível buscar a liturgia de hoje. Tente novamente em instantes.",
                code="LITURGIA_INDISPONIVEL",
            ) from exc

    return wrapped


class PostgresLiturgiaDiariaRepository(LiturgiaDiariaRepository):
    """Implementação de produção: cache em Postgres, busca sob demanda."""

    def __init__(self, pool: AsyncPool, fetcher: Fetcher = fetch_liturgia) -> None:
        self._pool = pool
        self._fetcher = _buscar_ou_falhar(fetcher)

    @staticmethod
    async def create_schema(pool: AsyncPool) -> None:
        await pool.execute(
            """
            CREATE TABLE IF NOT EXISTS liturgia_diaria (
                data DATE PRIMARY KEY,
                payload JSONB NOT NULL,
                criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """
        )

    async def get(self, dia: date) -> LiturgiaDiaria:
        row = await self._pool.fetchrow(
            "SELECT payload FROM liturgia_diaria WHERE data = $1", dia
        )
        if row is not None:
            return LiturgiaDiaria.model_validate(json.loads(row["payload"]))  # type: ignore[index]

        liturgia = await self._fetcher(dia)
        # `ON CONFLICT DO NOTHING`: se duas requisições baterem no mesmo
        # segundo no cache-miss (raro, mas possível), a segunda não quebra
        # numa violação de chave primária — só perde a própria gravação e
        # segue com o valor que já buscou.
        await self._pool.execute(
            """
            INSERT INTO liturgia_diaria (data, payload)
            VALUES ($1, $2::jsonb)
            ON CONFLICT (data) DO NOTHING
            """,
            dia,
            liturgia.model_dump_json(),
        )
        return liturgia


class InMemoryLiturgiaDiariaRepository(LiturgiaDiariaRepository):
    """Fake usada nos testes — mesma interface, sem rede nem Postgres."""

    def __init__(self, fetcher: Fetcher) -> None:
        self._fetcher = _buscar_ou_falhar(fetcher)
        self._cache: dict[date, LiturgiaDiaria] = {}

    async def get(self, dia: date) -> LiturgiaDiaria:
        if dia not in self._cache:
            self._cache[dia] = await self._fetcher(dia)
        return self._cache[dia]


def require_repository(
    repo: LiturgiaDiariaRepository | None,
) -> LiturgiaDiariaRepository:
    """Traduz "banco não configurado" em 503, não em 500 nem crash de boot."""
    if repo is None:
        raise ServiceUnavailableException(
            message="A liturgia diária está temporariamente indisponível.",
            code="LITURGIA_INDISPONIVEL",
        )
    return repo


__all__ = [
    "LiturgiaDiaria",
    "LiturgiaDiariaRepository",
    "PostgresLiturgiaDiariaRepository",
    "InMemoryLiturgiaDiariaRepository",
    "require_repository",
]
