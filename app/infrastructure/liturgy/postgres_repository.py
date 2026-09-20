"""Cache da liturgia diária em Postgres — só cache, não busca externa (ver
`app.infrastructure.liturgy.http_gateway` pra isso).
"""

from __future__ import annotations

import json
from datetime import date
from typing import Protocol

from app.domain.liturgy.entities import DailyLiturgy, LiturgicalReading
from app.domain.liturgy.repository import DailyLiturgyRepository


class AsyncPool(Protocol):
    """O subconjunto de `asyncpg.Pool` que este módulo usa — só para tipar."""

    async def execute(self, query: str, *args: object) -> str: ...
    async def fetchrow(self, query: str, *args: object) -> object | None: ...


def _reading_to_dict(reading: LiturgicalReading | None) -> dict[str, str] | None:
    if reading is None:
        return None
    return {"referencia": reading.reference, "texto": reading.text}


def _reading_from_dict(data: dict[str, str] | None) -> LiturgicalReading | None:
    if data is None:
        return None
    return LiturgicalReading(reference=data["referencia"], text=data["texto"])


def _liturgy_to_payload(liturgy: DailyLiturgy) -> str:
    """`DailyLiturgy` é um dataclass simples: sem `model_dump_json` do
    Pydantic, a serialização (inclusive a data, que o JSON não tem tipo
    nativo pra isso) é feita à mão.

    As chaves do JSON gravado permanecem em português (`cor_liturgica`,
    `celebracao`...) — é o formato já persistido em produção; mudar exigiria
    migração de dado, sem ganho nenhum, já que ninguém lê esse JSON fora
    deste módulo."""
    return json.dumps(
        {
            "data": liturgy.date.isoformat(),
            "cor_liturgica": liturgy.liturgical_color,
            "celebracao": liturgy.celebration,
            "primeira_leitura": _reading_to_dict(liturgy.first_reading),
            "salmo": _reading_to_dict(liturgy.psalm),
            "segunda_leitura": _reading_to_dict(liturgy.second_reading),
            "evangelho": _reading_to_dict(liturgy.gospel),
            "fonte": liturgy.source,
        }
    )


def _liturgy_from_payload(payload: dict[str, object]) -> DailyLiturgy:
    return DailyLiturgy(
        date=date.fromisoformat(payload["data"]),  # type: ignore[arg-type]
        liturgical_color=payload.get("cor_liturgica"),  # type: ignore[arg-type]
        celebration=payload.get("celebracao"),  # type: ignore[arg-type]
        first_reading=_reading_from_dict(payload["primeira_leitura"]),  # type: ignore[arg-type]
        psalm=_reading_from_dict(payload["salmo"]),  # type: ignore[arg-type]
        second_reading=_reading_from_dict(payload.get("segunda_leitura")),  # type: ignore[arg-type]
        gospel=_reading_from_dict(payload["evangelho"]),  # type: ignore[arg-type]
        source=payload["fonte"],  # type: ignore[arg-type]
    )


class PostgresDailyLiturgyRepository(DailyLiturgyRepository):
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

    async def get_cached(self, day: date) -> DailyLiturgy | None:
        row = await self._pool.fetchrow(
            "SELECT payload FROM liturgia_diaria WHERE data = $1", day
        )
        if row is None:
            return None
        return _liturgy_from_payload(json.loads(row["payload"]))  # type: ignore[index]

    async def save(self, day: date, liturgy: DailyLiturgy) -> None:
        # `ON CONFLICT DO NOTHING`: se duas requisições baterem no mesmo
        # segundo num cache-miss (raro, mas possível), a segunda não quebra
        # numa violação de chave primária — só perde a própria gravação.
        await self._pool.execute(
            """
            INSERT INTO liturgia_diaria (data, payload)
            VALUES ($1, $2::jsonb)
            ON CONFLICT (data) DO NOTHING
            """,
            day,
            _liturgy_to_payload(liturgy),
        )
