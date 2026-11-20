"""Rotas das métricas de visitas.

Só o servidor do site chama estas rotas (com `INTERNAL_API_SECRET`): o navegador
manda a visita para o próprio site, que a repassa com o IP e o navegador de quem
visitou. Assim não há chamada de outro domínio (que bloqueadores de anúncio
cortam) e ninguém de fora inventa visitas.

Gravar nunca derruba nada: sem banco, robô ou dado inválido, responde 204 e segue.
"""

from __future__ import annotations

import hmac
import json
import time
from datetime import UTC, datetime, timedelta, timezone

from fastapi import APIRouter, Header, Query, Request, Response

from app.application.metrics.summary import MAX_DAYS, get_summary
from app.core.config import settings
from app.core.exceptions import AppException, ServiceUnavailableException
from app.domain.metrics.entities import Ranked
from app.domain.metrics.repository import MetricsRepository
from app.domain.metrics.rules import build_hit

router = APIRouter(prefix="/api/metricas", tags=["métricas"])

_BRAZIL = timezone(timedelta(hours=-3))
OWN_HOSTS = ("compendio-catolico.com",)
MAX_PER_MINUTE = 60
_MAX_BODY = 2048

# IP → (minuto, quantas). Memória do processo: defesa contra flood de um IP só.
_per_minute: dict[str, tuple[int, int]] = {}


def _within_limit(ip: str) -> bool:
    minute = int(time.monotonic() // 60)
    seen_minute, count = _per_minute.get(ip, (minute, 0))
    count = count + 1 if seen_minute == minute else 1
    _per_minute[ip] = (minute, count)
    if len(_per_minute) > 50_000:  # não deixa o dicionário crescer sem fim
        _per_minute.clear()
    return count <= MAX_PER_MINUTE


def _require_secret(given: str) -> str:
    secret = settings.internal_api_secret
    if not secret:
        raise ServiceUnavailableException(
            message="As métricas estão indisponíveis.", code="METRICAS_INDISPONIVEIS"
        )
    if not hmac.compare_digest(given.encode(), secret.encode()):
        raise AppException(
            "Acesso não autorizado.", status_code=401, code="NAO_AUTORIZADO"
        )
    return secret


@router.post(
    "",
    status_code=204,
    response_class=Response,
    summary="Grava uma visita ou um evento",
)
async def record_hit(
    request: Request,
    x_internal_secret: str = Header(default=""),
    x_visitante_ip: str = Header(default="", max_length=64),
    x_visitante_ua: str = Header(default="", max_length=512),
) -> Response:
    secret = _require_secret(x_internal_secret)
    repo: MetricsRepository | None = getattr(
        request.app.state, "metrics_repository", None
    )
    body = await request.body()
    if repo is None or len(body) > _MAX_BODY or not _within_limit(x_visitante_ip):
        return Response(status_code=204)
    try:
        payload = json.loads(body)
    except ValueError:
        return Response(status_code=204)
    hit = build_hit(
        payload,
        ip=x_visitante_ip,
        user_agent=x_visitante_ua,
        day=datetime.now(_BRAZIL).date(),
        secret=secret,
        own_hosts=OWN_HOSTS,
    )
    if hit is not None:
        await repo.record(hit)
    return Response(status_code=204)


def _ranked(items: list[Ranked]) -> list[dict[str, object]]:
    return [{"nome": item.name, "total": item.count} for item in items]


@router.get("/resumo", summary="Resumo do painel de métricas")
async def summary(
    request: Request,
    dias: int = Query(default=30, ge=1, le=MAX_DAYS),
    x_internal_secret: str = Header(default=""),
) -> dict[str, object]:
    _require_secret(x_internal_secret)
    repo: MetricsRepository | None = getattr(
        request.app.state, "metrics_repository", None
    )
    if repo is None:
        raise ServiceUnavailableException(
            message="As métricas estão indisponíveis.", code="METRICAS_INDISPONIVEIS"
        )
    result = await get_summary(repo, today=datetime.now(_BRAZIL).date(), days=dias)
    return {
        "inicio": result.start.isoformat(),
        "fim": result.end.isoformat(),
        "gerado_em": datetime.now(UTC).isoformat(),
        "dias": [
            {"dia": d.day.isoformat(), "visitantes": d.visitors, "paginas": d.views}
            for d in result.days
        ],
        "visitantes": result.visitors,
        "paginas": result.views,
        "visitantes_antes": result.previous_visitors,
        "paginas_antes": result.previous_views,
        "paginas_mais_vistas": _ranked(result.top_pages),
        "origens": _ranked(result.top_referrers),
        "eventos": _ranked(result.events),
        "dispositivos": _ranked(result.devices),
    }
