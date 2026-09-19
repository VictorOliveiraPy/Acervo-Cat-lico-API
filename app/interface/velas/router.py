"""Rotas HTTP do mural de velas.

Registrado em `main.py` **antes** do router do acervo: `/api/velas` teria
que competir com a rota coringa `/api/{categoria}` se viesse depois, e
`velas` acabaria lido como um nome de categoria inexistente.

Fino de propósito: parseia a requisição, chama o use case, serializa a
resposta — nenhuma regra de negócio mora aqui.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from app.application.velas.acender_vela_use_case import AcenderVelaUseCase
from app.application.velas.listar_velas_use_case import ListarVelasUseCase
from app.core.config import settings
from app.core.exceptions import ServiceUnavailableException
from app.core.rate_limiting import RateLimiter, client_ip
from app.domain.velas.repository import VelasRepository
from app.interface.velas.schemas import (
    VelaCreateRequest,
    VelaPageResponse,
    VelaResponse,
)

router = APIRouter(prefix="/api/velas", tags=["velas"])

_rate_limiter = RateLimiter(window_seconds=20.0)


def get_velas_repository(request: Request) -> VelasRepository:
    """Lê o repositório setado no lifespan — `None` quando sem `DATABASE_URL`."""
    repo: VelasRepository | None = getattr(
        request.app.state, "velas_repository", None
    )
    if repo is None:
        raise ServiceUnavailableException(
            message="O mural de velas está temporariamente indisponível.",
            code="VELAS_INDISPONIVEL",
        )
    return repo


@router.get("", response_model=VelaPageResponse, summary="Mural de velas acesas")
async def list_velas(
    limit: int = Query(default=settings.default_page_size, ge=1),
    offset: int = Query(default=0, ge=0),
    repo: VelasRepository = Depends(get_velas_repository),
) -> VelaPageResponse:
    """Velas acesas por qualquer visitante, mais recentes primeiro."""
    limit = min(limit, settings.max_page_size)
    pagina = await ListarVelasUseCase(repo).execute(limit=limit, offset=offset)
    return VelaPageResponse(
        total=pagina.total,
        limit=limit,
        offset=offset,
        itens=[VelaResponse.from_entity(vela) for vela in pagina.itens],
    )


@router.post(
    "",
    response_model=VelaResponse,
    status_code=201,
    summary="Acende uma vela no mural",
)
async def create_vela(
    payload: VelaCreateRequest,
    request: Request,
    repo: VelasRepository = Depends(get_velas_repository),
) -> VelaResponse:
    """Registra uma vela pública — nome, intenção opcional e tipo escolhido."""
    _rate_limiter.check(client_ip(request))
    vela = await AcenderVelaUseCase(repo).execute(payload.to_entity())
    return VelaResponse.from_entity(vela)
