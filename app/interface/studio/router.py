"""Rotas do estúdio de vídeos.

Três públicos, três portas:
- `/api/reels`: o site lê os reels publicados (sem autenticação).
- `/api/admin/...`: o painel do site (segredo interno, só o servidor do site conhece)
  edita reels, pede vídeos e recebe links de envio para o R2.
- `/api/estudio/...`: o gerador no computador de quem administra (token próprio) pega
  pedidos da fila, conta o andamento, envia os arquivos e entrega o reel pronto.

Vídeo pronto entra como rascunho: só aparece no site depois de publicado no painel.
"""

from __future__ import annotations

import hmac
from typing import Annotated, Literal

from fastapi import APIRouter, Body, Header, Path, Query, Request, Response

from app.core.config import settings
from app.core.exceptions import (
    AppException,
    NotFoundException,
    ServiceUnavailableException,
)
from app.domain.studio.entities import Reel, VideoRequest
from app.domain.studio.repository import ReelRepository, VideoRequestRepository
from app.domain.studio.rules import (
    REEL_THEMES,
    ValidationError,
    clean_reel_patch,
    new_reel,
    new_request,
)
from app.infrastructure.storage.r2 import R2Config, delete_object, presign_url

router = APIRouter(tags=["estúdio"])

UPLOAD_SECONDS = 15 * 60
_FILES = {"video": ("mp4", "video/mp4"), "capa": ("jpg", "image/jpeg")}
SlugParam = Annotated[str, Path(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=80)]


# ----------------------------------------------------------------- dependências


def _check(given: str, expected: str | None, what: str) -> None:
    if not expected:
        raise ServiceUnavailableException(
            message=f"{what} indisponível.", code="ESTUDIO_INDISPONIVEL"
        )
    if not hmac.compare_digest(given.encode(), expected.encode()):
        raise AppException(
            "Acesso não autorizado.", status_code=401, code="NAO_AUTORIZADO"
        )


def _admin(secret: str) -> None:
    _check(secret, settings.internal_api_secret, "O painel")


def _worker(token: str) -> None:
    _check(token, settings.estudio_token, "O estúdio")


def _reels(request: Request) -> ReelRepository:
    repo: ReelRepository | None = getattr(request.app.state, "reel_repository", None)
    if repo is None:
        raise ServiceUnavailableException(
            message="Os vídeos estão indisponíveis.", code="REELS_INDISPONIVEIS"
        )
    return repo


def _requests(request: Request) -> VideoRequestRepository:
    repo: VideoRequestRepository | None = getattr(
        request.app.state, "video_request_repository", None
    )
    if repo is None:
        raise ServiceUnavailableException(
            message="O estúdio está indisponível.", code="ESTUDIO_INDISPONIVEL"
        )
    return repo


def _r2() -> R2Config:
    values = (
        settings.r2_account_id,
        settings.r2_bucket,
        settings.r2_access_key_id,
        settings.r2_secret_access_key,
    )
    if not all(values):
        raise ServiceUnavailableException(
            message="O envio de arquivos não está configurado.", code="R2_INDISPONIVEL"
        )
    account, bucket, key_id, secret = values
    return R2Config(
        account_id=str(account),
        bucket=str(bucket),
        access_key_id=str(key_id),
        secret_access_key=str(secret),
        public_base_url=settings.r2_public_base_url,
    )


def _invalid(error: ValidationError) -> AppException:
    return AppException(str(error), status_code=422, code="DADOS_INVALIDOS")


# ----------------------------------------------------------------- formatos


def _reel_json(reel: Reel) -> dict[str, object]:
    return {
        "slug": reel.slug,
        "titulo": reel.title,
        "legenda": reel.caption,
        "tema": reel.theme,
        "largura": reel.width,
        "altura": reel.height,
        "video_url": reel.video_url,
        "capa_url": reel.cover_url,
        "publicado": reel.published,
        "criado_em": reel.created_at.isoformat() if reel.created_at else None,
    }


def _request_json(req: VideoRequest) -> dict[str, object]:
    return {
        "id": req.id,
        "tema": req.theme,
        "pergunta": req.question,
        "notas": req.notes,
        "formato": req.format,
        "status": req.status,
        "etapa": req.stage,
        "progresso": req.progress,
        "erro": req.error,
        "slug": req.slug,
        "criado_em": req.created_at.isoformat() if req.created_at else None,
        "atualizado_em": req.updated_at.isoformat() if req.updated_at else None,
    }


def _upload(slug: str, kind: str) -> dict[str, str]:
    if kind not in _FILES:
        raise AppException(
            "tipo: video ou capa.", status_code=422, code="DADOS_INVALIDOS"
        )
    config = _r2()
    extension, content_type = _FILES[kind]
    key = f"reels/{slug}.{extension}"
    return {
        "upload_url": presign_url(config, "PUT", key, expires_seconds=UPLOAD_SECONDS),
        "public_url": config.public_url(key),
        "content_type": content_type,
    }


# ----------------------------------------------------------------- site


@router.get("/api/reels", summary="Reels publicados, do mais novo para o mais antigo")
async def list_reels(
    request: Request,
    tema: str | None = Query(default=None),
    limit: int = Query(default=24, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict[str, object]:
    if tema is not None and tema not in REEL_THEMES:
        raise AppException(
            "tema desconhecido.", status_code=422, code="DADOS_INVALIDOS"
        )
    reels, total = await _reels(request).list(
        theme=tema, only_published=True, limit=limit, offset=offset
    )
    return {"itens": [_reel_json(r) for r in reels], "total": total}


# ----------------------------------------------------------------- painel


@router.get("/api/admin/reels", summary="Todos os reels, inclusive rascunhos")
async def admin_list_reels(
    request: Request,
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    x_internal_secret: str = Header(default=""),
) -> dict[str, object]:
    _admin(x_internal_secret)
    reels, total = await _reels(request).list(
        theme=None, only_published=False, limit=limit, offset=offset
    )
    return {"itens": [_reel_json(r) for r in reels], "total": total}


@router.post(
    "/api/admin/reels",
    status_code=201,
    summary="Cadastra um reel (vídeo já enviado ao R2)",
)
async def admin_create_reel(
    request: Request,
    body: dict[str, object] = Body(...),
    x_internal_secret: str = Header(default=""),
) -> dict[str, object]:
    _admin(x_internal_secret)
    try:
        reel = new_reel(body)
    except ValidationError as error:
        raise _invalid(error) from error
    try:
        return _reel_json(await _reels(request).create(reel))
    except KeyError as error:
        raise AppException(
            "Já existe um vídeo com esse endereço.", status_code=409, code="SLUG_EM_USO"
        ) from error


@router.patch(
    "/api/admin/reels/{slug}", summary="Edita título, legenda, tema ou publicação"
)
async def admin_update_reel(
    request: Request,
    slug: SlugParam,
    body: dict[str, object] = Body(...),
    x_internal_secret: str = Header(default=""),
) -> dict[str, object]:
    _admin(x_internal_secret)
    try:
        patch = clean_reel_patch(body)
    except ValidationError as error:
        raise _invalid(error) from error
    reel = await _reels(request).update(slug, patch)
    if reel is None:
        raise NotFoundException("Vídeo não encontrado.", code="REEL_NAO_ENCONTRADO")
    return _reel_json(reel)


@router.delete(
    "/api/admin/reels/{slug}",
    status_code=204,
    response_class=Response,
    summary="Apaga o reel e os arquivos no R2",
)
async def admin_delete_reel(
    request: Request, slug: SlugParam, x_internal_secret: str = Header(default="")
) -> Response:
    _admin(x_internal_secret)
    repo = _reels(request)
    reel = await repo.get(slug)
    if reel is None:
        raise NotFoundException("Vídeo não encontrado.", code="REEL_NAO_ENCONTRADO")
    await repo.delete(slug)
    # Só o que está no nosso bucket; capas antigas servidas pelo próprio site ficam lá.
    prefix = settings.r2_public_base_url.rstrip("/") + "/"
    keys = [
        url.removeprefix(prefix)
        for url in (reel.video_url, reel.cover_url)
        if url.startswith(prefix)
    ]
    if keys:
        config = _r2()
        for key in keys:
            await delete_object(config, key)
    return Response(status_code=204)


@router.post("/api/admin/uploads", summary="Link de envio ao R2 para o vídeo ou a capa")
async def admin_upload(
    body: dict[str, object] = Body(...), x_internal_secret: str = Header(default="")
) -> dict[str, str]:
    _admin(x_internal_secret)
    slug = body.get("slug")
    if not isinstance(slug, str):
        raise AppException("slug obrigatório.", status_code=422, code="DADOS_INVALIDOS")
    try:
        new_reel(
            {
                "slug": slug,
                "titulo": "x",
                "tema": "santos",
                "largura": 1,
                "altura": 1,
                "video_url": "/x",
                "capa_url": "/x",
            }
        )
    except ValidationError as error:
        raise _invalid(error) from error
    return _upload(slug, str(body.get("tipo")))


@router.get("/api/admin/pedidos", summary="Pedidos de vídeo, do mais novo")
async def admin_list_requests(
    request: Request, x_internal_secret: str = Header(default="")
) -> list[dict[str, object]]:
    _admin(x_internal_secret)
    return [_request_json(r) for r in await _requests(request).list_recent(50)]


@router.post(
    "/api/admin/pedidos", status_code=201, summary="Pede um vídeo novo ao gerador"
)
async def admin_create_request(
    request: Request,
    body: dict[str, object] = Body(...),
    x_internal_secret: str = Header(default=""),
) -> dict[str, object]:
    _admin(x_internal_secret)
    try:
        new = new_request(body)
    except ValidationError as error:
        raise _invalid(error) from error
    return _request_json(await _requests(request).create(new))


async def _set_status(
    request: Request, request_id: int, status: Literal["na_fila", "cancelado"]
) -> dict[str, object]:
    fields: dict[str, object] = {
        "status": status,
        "stage": "",
        "progress": 0,
        "error": "",
    }
    updated = await _requests(request).update(request_id, **fields)
    if updated is None:
        raise NotFoundException("Pedido não encontrado.", code="PEDIDO_NAO_ENCONTRADO")
    return _request_json(updated)


@router.post(
    "/api/admin/pedidos/{request_id}/refazer", summary="Põe o pedido de volta na fila"
)
async def admin_retry(
    request: Request, request_id: int, x_internal_secret: str = Header(default="")
) -> dict[str, object]:
    _admin(x_internal_secret)
    return await _set_status(request, request_id, "na_fila")


@router.post("/api/admin/pedidos/{request_id}/cancelar", summary="Cancela o pedido")
async def admin_cancel(
    request: Request, request_id: int, x_internal_secret: str = Header(default="")
) -> dict[str, object]:
    _admin(x_internal_secret)
    return await _set_status(request, request_id, "cancelado")


# ----------------------------------------------------------------- gerador


@router.post(
    "/api/estudio/proximo", response_model=None, summary="Pega o próximo pedido da fila"
)
async def worker_next(
    request: Request, x_estudio_token: str = Header(default="")
) -> Response | dict[str, object]:
    _worker(x_estudio_token)
    _r2()  # sem o R2 configurado, o vídeo pronto não teria para onde ir
    claimed = await _requests(request).claim_next()
    return _request_json(claimed) if claimed else Response(status_code=204)


async def _own(request: Request, request_id: int) -> VideoRequest:
    found = await _requests(request).get(request_id)
    if found is None:
        raise NotFoundException("Pedido não encontrado.", code="PEDIDO_NAO_ENCONTRADO")
    return found


@router.post(
    "/api/estudio/pedidos/{request_id}/andamento",
    status_code=204,
    response_class=Response,
)
async def worker_progress(
    request: Request,
    request_id: int,
    body: dict[str, object] = Body(...),
    x_estudio_token: str = Header(default=""),
) -> Response:
    _worker(x_estudio_token)
    await _own(request, request_id)
    stage = str(body.get("etapa", ""))[:200]
    progress = body.get("progresso", 0)
    progress = max(0, min(100, progress)) if isinstance(progress, int) else 0
    await _requests(request).update(request_id, stage=stage, progress=progress)
    return Response(status_code=204)


@router.post("/api/estudio/pedidos/{request_id}/upload")
async def worker_upload(
    request: Request,
    request_id: int,
    body: dict[str, object] = Body(...),
    x_estudio_token: str = Header(default=""),
) -> dict[str, str]:
    _worker(x_estudio_token)
    await _own(request, request_id)
    slug = body.get("slug")
    if not isinstance(slug, str):
        raise AppException("slug obrigatório.", status_code=422, code="DADOS_INVALIDOS")
    return _upload(slug, str(body.get("tipo")))


@router.post("/api/estudio/pedidos/{request_id}/pronto", status_code=201)
async def worker_done(
    request: Request,
    request_id: int,
    body: dict[str, object] = Body(...),
    x_estudio_token: str = Header(default=""),
) -> dict[str, object]:
    _worker(x_estudio_token)
    await _own(request, request_id)
    config = _r2()
    slug = body.get("slug")
    theme = body.get("tema") if body.get("tema") in REEL_THEMES else "curiosidades"
    try:
        reel = new_reel(
            {
                **body,
                "tema": theme,
                "publicado": False,
                "video_url": config.public_url(f"reels/{slug}.mp4"),
                "capa_url": config.public_url(f"reels/{slug}.jpg"),
            }
        )
    except ValidationError as error:
        raise _invalid(error) from error
    try:
        created = await _reels(request).create(reel)
    except KeyError as error:
        raise AppException(
            "Já existe um vídeo com esse endereço.", status_code=409, code="SLUG_EM_USO"
        ) from error
    await _requests(request).update(
        request_id, status="pronto", stage="Pronto", progress=100, slug=reel.slug
    )
    return _reel_json(created)


@router.post(
    "/api/estudio/pedidos/{request_id}/erro", status_code=204, response_class=Response
)
async def worker_error(
    request: Request,
    request_id: int,
    body: dict[str, object] = Body(...),
    x_estudio_token: str = Header(default=""),
) -> Response:
    _worker(x_estudio_token)
    await _own(request, request_id)
    message = str(body.get("mensagem", "Erro sem descrição."))[:500]
    await _requests(request).update(request_id, status="erro", error=message)
    return Response(status_code=204)
