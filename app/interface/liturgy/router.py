"""Rota HTTP da liturgia diária.

Registrado em `main.py` **antes** do router do acervo — mesmo motivo de
`interface.candles.router`: `/api/liturgia-diaria` teria que competir com a
rota coringa `/api/{categoria}`, e `liturgia-diaria` acabaria lido como um
nome de categoria inexistente.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query, Request

from app.application.liturgy.get_daily_liturgy_use_case import GetDailyLiturgyUseCase
from app.core.exceptions import ServiceUnavailableException
from app.domain.liturgy.gateway import LiturgyExternalGateway
from app.domain.liturgy.repository import DailyLiturgyRepository
from app.infrastructure.liturgy.http_gateway import HttpLiturgyGateway
from app.interface.liturgy.schemas import DailyLiturgyResponse

router = APIRouter(prefix="/api/liturgia-diaria", tags=["liturgia-diaria"])

# Fuso fixo (UTC-3), não `zoneinfo("America/Sao_Paulo")`: o Brasil não usa
# horário de verão desde 2019, e um offset fixo não depende da base de dados
# de fusos horários (tzdata) estar instalada na imagem de deploy.
_BRAZIL = timezone(timedelta(hours=-3))

# Sem estado próprio (não fala rede na criação) — uma instância por
# requisição não tem custo real, e evita compartilhar estado entre elas.
_default_gateway = HttpLiturgyGateway()


def _today_in_brazil() -> date:
    return datetime.now(_BRAZIL).date()


def get_liturgy_repository(request: Request) -> DailyLiturgyRepository:
    """Lê o repositório setado no lifespan — `None` quando sem `DATABASE_URL`."""
    repo: DailyLiturgyRepository | None = getattr(
        request.app.state, "liturgy_repository", None
    )
    if repo is None:
        raise ServiceUnavailableException(
            message="A liturgia diária está temporariamente indisponível.",
            code="LITURGIA_INDISPONIVEL",
        )
    return repo


def get_liturgy_gateway(request: Request) -> LiturgyExternalGateway:
    """Gateway real por padrão; testes sobrescrevem via
    `app.state.liturgy_gateway` com um fake, sem precisar mexer aqui."""
    return getattr(request.app.state, "liturgy_gateway", None) or _default_gateway


@router.get("", response_model=DailyLiturgyResponse, summary="Liturgia do dia (leituras da Missa)")
async def get_daily_liturgy(
    data: date | None = Query(
        default=None,
        description="Data específica (AAAA-MM-DD). Padrão: hoje, horário de Brasília.",
    ),
    repo: DailyLiturgyRepository = Depends(get_liturgy_repository),
    gateway: LiturgyExternalGateway = Depends(get_liturgy_gateway),
) -> DailyLiturgyResponse:
    """Cor litúrgica, celebração do dia e as leituras da Missa (1ª leitura,
    salmo, 2ª leitura quando houver, e evangelho)."""
    day = data or _today_in_brazil()
    liturgy = await GetDailyLiturgyUseCase(repo, gateway).execute(day)
    return DailyLiturgyResponse.from_entity(liturgy)
