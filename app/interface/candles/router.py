"""Rotas HTTP do mural de velas.

Registrado em `main.py` **antes** do router do acervo: `/api/velas` teria
que competir com a rota coringa `/api/{categoria}` se viesse depois, e
`velas` acabaria lido como um nome de categoria inexistente.

Fino de propósito: parseia a requisição, chama o use case, serializa a
resposta — nenhuma regra de negócio mora aqui.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from app.application.candles.light_candle_use_case import LightCandleUseCase
from app.application.candles.list_candles_use_case import ListCandlesUseCase
from app.core.config import settings
from app.core.exceptions import ServiceUnavailableException
from app.core.rate_limiting import RateLimiter, client_ip
from app.domain.candles.repository import CandleRepository
from app.interface.candles.schemas import (
    CandleCreateRequest,
    CandlePageResponse,
    CandleResponse,
)

router = APIRouter(prefix="/api/velas", tags=["velas"])

_rate_limiter = RateLimiter(window_seconds=20.0)


def get_candle_repository(request: Request) -> CandleRepository:
    """Lê o repositório setado no lifespan — `None` quando sem `DATABASE_URL`."""
    repo: CandleRepository | None = getattr(
        request.app.state, "candle_repository", None
    )
    if repo is None:
        raise ServiceUnavailableException(
            message="O mural de velas está temporariamente indisponível.",
            code="VELAS_INDISPONIVEL",
        )
    return repo


@router.get("", response_model=CandlePageResponse, summary="Mural de velas acesas")
async def list_candles(
    limit: int = Query(default=settings.default_page_size, ge=1),
    offset: int = Query(default=0, ge=0),
    repo: CandleRepository = Depends(get_candle_repository),
) -> CandlePageResponse:
    """Velas acesas por qualquer visitante, mais recentes primeiro."""
    limit = min(limit, settings.max_page_size)
    page = await ListCandlesUseCase(repo).execute(limit=limit, offset=offset)
    return CandlePageResponse(
        total=page.total,
        limit=limit,
        offset=offset,
        itens=[CandleResponse.from_entity(candle) for candle in page.items],
    )


@router.post(
    "",
    response_model=CandleResponse,
    status_code=201,
    summary="Acende uma vela no mural",
)
async def create_candle(
    payload: CandleCreateRequest,
    request: Request,
    repo: CandleRepository = Depends(get_candle_repository),
) -> CandleResponse:
    """Registra uma vela pública — nome, intenção opcional e tipo escolhido."""
    _rate_limiter.check(client_ip(request))
    candle = await LightCandleUseCase(repo).execute(payload.to_entity())
    return CandleResponse.from_entity(candle)
