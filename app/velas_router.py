"""Rotas HTTP do mural de velas.

Registrado em `main.py` **antes** do router do acervo: `/api/velas` teria
que competir com a rota coringa `/api/{categoria}` se viesse depois, e
`velas` acabaria lido como um nome de categoria inexistente.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from app.config import settings
from app.velas_models import Vela, VelaCreate, VelaPage
from app.velas_repository import (
    RateLimiter,
    VelasRepository,
    client_ip,
    require_repository,
)

router = APIRouter(prefix="/api/velas", tags=["velas"])

_rate_limiter = RateLimiter()


def get_velas_repository(request: Request) -> VelasRepository:
    """Lê o repositório setado no lifespan — `None` quando sem `DATABASE_URL`."""
    repo: VelasRepository | None = getattr(
        request.app.state, "velas_repository", None
    )
    return require_repository(repo)


@router.get("", response_model=VelaPage, summary="Mural de velas acesas")
async def list_velas(
    limit: int = Query(default=settings.default_page_size, ge=1),
    offset: int = Query(default=0, ge=0),
    repo: VelasRepository = Depends(get_velas_repository),
) -> VelaPage:
    """Velas acesas por qualquer visitante, mais recentes primeiro."""
    limit = min(limit, settings.max_page_size)
    itens, total = await repo.list_page(limit=limit, offset=offset)
    return VelaPage(total=total, limit=limit, offset=offset, itens=itens)


@router.post(
    "",
    response_model=Vela,
    status_code=201,
    summary="Acende uma vela no mural",
)
async def create_vela(
    payload: VelaCreate,
    request: Request,
    repo: VelasRepository = Depends(get_velas_repository),
) -> Vela:
    """Registra uma vela pública — nome, intenção opcional e tipo escolhido."""
    _rate_limiter.check(client_ip(request))
    return await repo.create(payload)
