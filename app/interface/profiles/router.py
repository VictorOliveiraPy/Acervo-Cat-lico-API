"""Rotas do perfil (`/api/perfil`) e do ranking (`/api/ranking`).

O login acontece no site, que fala com estas rotas de servidor para servidor. O
perfil exige o segredo compartilhado `INTERNAL_API_SECRET`, e sem ele as rotas
respondem 503: sem isso, qualquer um poderia agir em nome de outra pessoa só
informando um `sub`. Registrado antes do router do acervo em `main.py`, porque
`/api/perfil` competiria com a rota coringa `/api/{categoria}`.
"""

from __future__ import annotations

import hmac

from fastapi import APIRouter, Depends, Header, Query, Request, Response

from app.core.config import settings
from app.core.exceptions import (
    AppException,
    NotFoundException,
    ServiceUnavailableException,
)
from app.domain.profiles.repository import ProfileRepository
from app.interface.profiles.schemas import (
    LessonsRequest,
    ProfileResponse,
    ProfileSyncRequest,
    ProfileUpdateRequest,
    RankingRowResponse,
)

router = APIRouter(prefix="/api", tags=["perfil"])

RANKING_MAX = 100


def get_profile_repository(request: Request) -> ProfileRepository:
    repo: ProfileRepository | None = getattr(request.app.state, "profile_repository", None)
    if repo is None:
        raise ServiceUnavailableException(
            message="Os perfis estão temporariamente indisponíveis.",
            code="PERFIL_INDISPONIVEL",
        )
    return repo


def authenticated_subject(
    x_internal_secret: str = Header(default=""),
    x_user_sub: str = Header(default="", max_length=255),
) -> str:
    """Só o servidor do site conhece o segredo; é ele quem atesta o `sub` do login."""
    secret = settings.internal_api_secret
    if not secret:
        raise ServiceUnavailableException(
            message="Os perfis estão temporariamente indisponíveis.",
            code="PERFIL_INDISPONIVEL",
        )
    if not hmac.compare_digest(x_internal_secret.encode(), secret.encode()) or not x_user_sub:
        raise AppException("Acesso não autorizado.", status_code=401, code="NAO_AUTORIZADO")
    return x_user_sub


def _found(profile: object) -> object:
    if profile is None:
        raise NotFoundException(message="Perfil não encontrado.", code="PERFIL_NAO_ENCONTRADO")
    return profile


@router.post("/perfil", response_model=ProfileResponse)
async def sync_profile(
    payload: ProfileSyncRequest,
    subject: str = Depends(authenticated_subject),
    repo: ProfileRepository = Depends(get_profile_repository),
) -> ProfileResponse:
    """Devolve o perfil, criando-o no primeiro acesso."""
    return ProfileResponse.from_entity(await repo.ensure(subject, payload.nome))


@router.put("/perfil", response_model=ProfileResponse)
async def update_profile(
    payload: ProfileUpdateRequest,
    subject: str = Depends(authenticated_subject),
    repo: ProfileRepository = Depends(get_profile_repository),
) -> ProfileResponse:
    profile = await repo.update(subject, payload.nome, payload.preferencias, payload.no_ranking)
    return ProfileResponse.from_entity(_found(profile))  # type: ignore[arg-type]


@router.post("/perfil/licoes", response_model=ProfileResponse)
async def complete_lessons(
    payload: LessonsRequest,
    subject: str = Depends(authenticated_subject),
    repo: ProfileRepository = Depends(get_profile_repository),
) -> ProfileResponse:
    """Conclui lições; repetir uma lição não soma pontos de novo."""
    profile = await repo.complete_lessons(subject, payload.licoes)
    return ProfileResponse.from_entity(_found(profile))  # type: ignore[arg-type]


@router.delete("/perfil", status_code=204, response_class=Response, response_model=None)
async def delete_profile(
    subject: str = Depends(authenticated_subject),
    repo: ProfileRepository = Depends(get_profile_repository),
) -> None:
    """Apaga o perfil e o progresso, a pedido da própria pessoa."""
    await repo.delete(subject)


@router.get("/ranking", response_model=list[RankingRowResponse])
async def ranking(
    limit: int = Query(default=50, ge=1, le=RANKING_MAX),
    repo: ProfileRepository = Depends(get_profile_repository),
) -> list[RankingRowResponse]:
    """Público: só quem optou por aparecer, com nome de exibição e pontos."""
    return [RankingRowResponse.from_entity(row) for row in await repo.ranking(limit)]
