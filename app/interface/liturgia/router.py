"""Rota HTTP da liturgia diária.

Registrado em `main.py` **antes** do router do acervo — mesmo motivo de
`interface.velas.router`: `/api/liturgia-diaria` teria que competir com a
rota coringa `/api/{categoria}`, e `liturgia-diaria` acabaria lido como um
nome de categoria inexistente.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query, Request

from app.application.liturgia.obter_liturgia_do_dia_use_case import (
    ObterLiturgiaDoDiaUseCase,
)
from app.core.exceptions import ServiceUnavailableException
from app.domain.liturgia.gateway import LiturgiaExternalGateway
from app.domain.liturgia.repository import LiturgiaDiariaRepository
from app.infrastructure.liturgia.http_gateway import HttpLiturgiaGateway
from app.interface.liturgia.schemas import LiturgiaDiariaResponse

router = APIRouter(prefix="/api/liturgia-diaria", tags=["liturgia-diaria"])

# Fuso fixo (UTC-3), não `zoneinfo("America/Sao_Paulo")`: o Brasil não usa
# horário de verão desde 2019, e um offset fixo não depende da base de dados
# de fusos horários (tzdata) estar instalada na imagem de deploy.
_BRASIL = timezone(timedelta(hours=-3))

# Sem estado próprio (não fala rede na criação) — uma instância por
# requisição não tem custo real, e evita compartilhar estado entre elas.
_gateway_padrao = HttpLiturgiaGateway()


def _hoje_brasil() -> date:
    return datetime.now(_BRASIL).date()


def get_liturgia_repository(request: Request) -> LiturgiaDiariaRepository:
    """Lê o repositório setado no lifespan — `None` quando sem `DATABASE_URL`."""
    repo: LiturgiaDiariaRepository | None = getattr(
        request.app.state, "liturgia_repository", None
    )
    if repo is None:
        raise ServiceUnavailableException(
            message="A liturgia diária está temporariamente indisponível.",
            code="LITURGIA_INDISPONIVEL",
        )
    return repo


def get_liturgia_gateway(request: Request) -> LiturgiaExternalGateway:
    """Gateway real por padrão; testes sobrescrevem via
    `app.state.liturgia_gateway` com um fake, sem precisar mexer aqui."""
    return getattr(request.app.state, "liturgia_gateway", None) or _gateway_padrao


@router.get("", response_model=LiturgiaDiariaResponse, summary="Liturgia do dia (leituras da Missa)")
async def get_liturgia_diaria(
    data: date | None = Query(
        default=None,
        description="Data específica (AAAA-MM-DD). Padrão: hoje, horário de Brasília.",
    ),
    repo: LiturgiaDiariaRepository = Depends(get_liturgia_repository),
    gateway: LiturgiaExternalGateway = Depends(get_liturgia_gateway),
) -> LiturgiaDiariaResponse:
    """Cor litúrgica, celebração do dia e as leituras da Missa (1ª leitura,
    salmo, 2ª leitura quando houver, e evangelho)."""
    dia = data or _hoje_brasil()
    liturgia = await ObterLiturgiaDoDiaUseCase(repo, gateway).execute(dia)
    return LiturgiaDiariaResponse.from_entity(liturgia)
