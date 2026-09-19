"""Cache da liturgia diária em Postgres — só cache, não busca externa (ver
`app.infrastructure.liturgia.http_gateway` pra isso).
"""

from __future__ import annotations

import json
from datetime import date
from typing import Protocol

from app.domain.liturgia.entities import LeituraLiturgica, LiturgiaDiaria
from app.domain.liturgia.repository import LiturgiaDiariaRepository


class AsyncPool(Protocol):
    """O subconjunto de `asyncpg.Pool` que este módulo usa — só para tipar."""

    async def execute(self, query: str, *args: object) -> str: ...
    async def fetchrow(self, query: str, *args: object) -> object | None: ...


def _leitura_para_dict(leitura: LeituraLiturgica | None) -> dict[str, str] | None:
    if leitura is None:
        return None
    return {"referencia": leitura.referencia, "texto": leitura.texto}


def _leitura_de_dict(data: dict[str, str] | None) -> LeituraLiturgica | None:
    if data is None:
        return None
    return LeituraLiturgica(referencia=data["referencia"], texto=data["texto"])


def _liturgia_para_payload(liturgia: LiturgiaDiaria) -> str:
    """`LiturgiaDiaria` é um dataclass simples: sem `model_dump_json` do
    Pydantic, a serialização (inclusive a data, que o JSON não tem tipo
    nativo pra isso) é feita à mão."""
    return json.dumps(
        {
            "data": liturgia.data.isoformat(),
            "cor_liturgica": liturgia.cor_liturgica,
            "celebracao": liturgia.celebracao,
            "primeira_leitura": _leitura_para_dict(liturgia.primeira_leitura),
            "salmo": _leitura_para_dict(liturgia.salmo),
            "segunda_leitura": _leitura_para_dict(liturgia.segunda_leitura),
            "evangelho": _leitura_para_dict(liturgia.evangelho),
            "fonte": liturgia.fonte,
        }
    )


def _liturgia_de_payload(payload: dict[str, object]) -> LiturgiaDiaria:
    return LiturgiaDiaria(
        data=date.fromisoformat(payload["data"]),  # type: ignore[arg-type]
        cor_liturgica=payload.get("cor_liturgica"),  # type: ignore[arg-type]
        celebracao=payload.get("celebracao"),  # type: ignore[arg-type]
        primeira_leitura=_leitura_de_dict(payload["primeira_leitura"]),  # type: ignore[arg-type]
        salmo=_leitura_de_dict(payload["salmo"]),  # type: ignore[arg-type]
        segunda_leitura=_leitura_de_dict(payload.get("segunda_leitura")),  # type: ignore[arg-type]
        evangelho=_leitura_de_dict(payload["evangelho"]),  # type: ignore[arg-type]
        fonte=payload["fonte"],  # type: ignore[arg-type]
    )


class PostgresLiturgiaDiariaRepository(LiturgiaDiariaRepository):
    """Implementação de produção: cache em Postgres."""

    def __init__(self, pool: AsyncPool) -> None:
        self._pool = pool

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

    async def get_cached(self, dia: date) -> LiturgiaDiaria | None:
        row = await self._pool.fetchrow(
            "SELECT payload FROM liturgia_diaria WHERE data = $1", dia
        )
        if row is None:
            return None
        return _liturgia_de_payload(json.loads(row["payload"]))  # type: ignore[index]

    async def save(self, dia: date, liturgia: LiturgiaDiaria) -> None:
        # `ON CONFLICT DO NOTHING`: se duas requisições baterem no mesmo
        # segundo num cache-miss (raro, mas possível), a segunda não quebra
        # numa violação de chave primária — só perde a própria gravação.
        await self._pool.execute(
            """
            INSERT INTO liturgia_diaria (data, payload)
            VALUES ($1, $2::jsonb)
            ON CONFLICT (data) DO NOTHING
            """,
            dia,
            _liturgia_para_payload(liturgia),
        )
