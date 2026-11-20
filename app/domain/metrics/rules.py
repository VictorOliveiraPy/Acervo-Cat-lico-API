"""Regras puras das métricas: o que conta, como limpar e como anonimizar.

Privacidade por construção: nada de cookie, e o IP só entra num hash junto com o
navegador, o dia e um segredo do servidor. Como o dia faz parte do hash, a mesma
pessoa vira outro código amanhã: dá para contar visitantes de cada dia, não para
seguir alguém ao longo do tempo.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable, Mapping
from datetime import date
from urllib.parse import urlsplit

from app.domain.metrics.entities import Device, HitKind, NewHit

# Os mesmos nomes do `trackEvent` do front (lib/analytics.ts).
EVENT_NAMES: frozenset[str] = frozenset(
    {
        "search_submitted",
        "candle_lit",
        "liturgy_opened",
        "entry_favorited",
        "entry_shared",
        "lesson_started",
        "lesson_completed",
        "calendar_subscribed",
        "prayer_action",
    }
)

_BOT = re.compile(
    r"bot|crawl|spider|slurp|headless|lighthouse|preview|facebookexternalhit|whatsapp|"
    r"telegram|discord|curl|wget|python|httpx|axios|node-fetch|go-http",
    re.IGNORECASE,
)
_PHONE = re.compile(r"mobile|android|iphone|ipod|ipad", re.IGNORECASE)
_MAX_PATH = 200


def is_bot(user_agent: str) -> bool:
    """Robôs, prévias de link e agentes vazios não são gente visitando."""
    return not user_agent.strip() or bool(_BOT.search(user_agent))


def device_of(user_agent: str) -> Device:
    return "celular" if _PHONE.search(user_agent) else "computador"


def visitor_id(ip: str, user_agent: str, day: date, secret: str) -> str:
    raw = f"{secret}|{day.isoformat()}|{ip}|{user_agent}".encode()
    return hashlib.sha256(raw).hexdigest()[:16]


def clean_path(raw: str) -> str | None:
    """Só o caminho interno (`/santos/x`), sem busca nem âncora; o resto é descartado."""
    if not raw.startswith("/") or raw.startswith("//"):
        return None
    path = re.split(r"[?#]", raw, maxsplit=1)[0]
    if len(path) > _MAX_PATH:
        return None
    return path.rstrip("/") or "/"


def referrer_host(raw: str, own_hosts: Iterable[str]) -> str | None:
    """Domínio externo que trouxe a visita; o próprio site e lixo viram `None`."""
    try:
        parts = urlsplit(raw)
    except ValueError:
        return None
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return None
    host = parts.hostname.removeprefix("www.")
    own = {h.removeprefix("www.") for h in own_hosts}
    return None if host in own else host


def build_hit(
    payload: Mapping[str, object],
    *,
    ip: str,
    user_agent: str,
    day: date,
    secret: str,
    own_hosts: Iterable[str],
) -> NewHit | None:
    """A visita a gravar, ou `None` quando não deve contar (robô, dado inválido)."""
    if not isinstance(payload, Mapping) or is_bot(user_agent):
        return None
    tipo = payload.get("tipo")
    path = clean_path(str(payload.get("caminho", "")))
    if path is None:
        return None
    if tipo == "pagina":
        kind: HitKind = "pagina"
    elif tipo == "evento":
        kind = "evento"
    else:
        return None
    event = payload.get("evento") if kind == "evento" else None
    if kind == "evento" and event not in EVENT_NAMES:
        return None
    referrer = payload.get("referencia")
    return NewHit(
        day=day,
        kind=kind,
        path=path,
        event=str(event) if event else None,
        referrer=referrer_host(referrer, own_hosts)
        if isinstance(referrer, str)
        else None,
        device=device_of(user_agent),
        visitor=visitor_id(ip, user_agent, day, secret),
    )
