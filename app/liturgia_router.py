"""Rota HTTP da liturgia diária.

Registrado em `main.py` **antes** do router do acervo — mesmo motivo de
`velas_router.py`: `/api/liturgia-diaria` teria que competir com a rota
coringa `/api/{categoria}`, e `liturgia-diaria` acabaria lido como um nome
de categoria inexistente.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query, Request

from app.liturgia_models import LiturgiaDiaria
from app.liturgia_repository import LiturgiaDiariaRepository, require_repository

router = APIRouter(prefix="/api/liturgia-diaria", tags=["liturgia-diaria"])

# Fuso fixo (UTC-3), não `zoneinfo("America/Sao_Paulo")`: o Brasil não usa
# horário de verão desde 2019, e um offset fixo não depende da base de dados
# de fusos horários (tzdata) estar instalada na imagem de deploy.
_BRASIL = timezone(timedelta(hours=-3))


def _hoje_brasil() -> date:
    return datetime.now(_BRASIL).date()


def get_liturgia_repository(request: Request) -> LiturgiaDiariaRepository:
    """Lê o repositório setado no lifespan — `None` quando sem `DATABASE_URL`."""
    repo: LiturgiaDiariaRepository | None = getattr(
        request.app.state, "liturgia_repository", None
    )
    return require_repository(repo)


@router.get("", response_model=LiturgiaDiaria, summary="Liturgia do dia (leituras da Missa)")
async def get_liturgia_diaria(
    data: date | None = Query(
        default=None,
        description="Data específica (AAAA-MM-DD). Padrão: hoje, horário de Brasília.",
    ),
    repo: LiturgiaDiariaRepository = Depends(get_liturgia_repository),
) -> LiturgiaDiaria:
    """Cor litúrgica, celebração do dia e as leituras da Missa (1ª leitura,
    salmo, 2ª leitura quando houver, e evangelho)."""
    dia = data or _hoje_brasil()
    return await repo.get(dia)
