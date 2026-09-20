"""Busca a liturgia de um dia numa fonte externa via HTTP.

A fonte (`api-liturgia-diaria.vercel.app`, um agregador de terceiros que lê
de sagradaliturgia.com.br) NÃO é um serviço oficial da CNBB nem do
Vaticano — é o serviço aberto mais completo e estável em português que
encontramos; a CNBB não expõe uma API pública própria. Isolado neste módulo
de propósito: trocar de fonte no futuro (se surgir uma oficial) é escrever
outra implementação de `LiturgyExternalGateway` — o use case e o
repositório de cache não sabem de onde os dados vêm.
"""

from __future__ import annotations

import html
import logging
import re
from datetime import date
from typing import Any

import httpx

from app.domain.liturgy.entities import DailyLiturgy, LiturgicalReading
from app.domain.liturgy.exceptions import LiturgyFetchError
from app.domain.liturgy.gateway import LiturgyExternalGateway

logger = logging.getLogger(__name__)

_API_URL = "https://api-liturgia-diaria.vercel.app/"
_TIMEOUT_SECONDS = 10.0

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(value: str | None) -> str:
    """Remove tags HTML simples (`<b>`, `<br/>`) e decodifica entidades."""
    if not value:
        return ""
    text = _TAG_RE.sub(" ", value)
    text = html.unescape(text)
    return " ".join(text.split())


def _parse_reading(raw: dict[str, Any], reference_key: str) -> LiturgicalReading:
    reference = _strip_html(raw.get(reference_key))
    text = _strip_html(raw.get("text"))
    return LiturgicalReading(reference=reference, text=text)


def _parse_psalm(raw: dict[str, Any]) -> LiturgicalReading:
    reference = _strip_html(raw.get("title"))
    response = _strip_html(raw.get("response"))
    lines = [_strip_html(line) for line in raw.get("content_psalm", [])]
    text = "\n".join([response, *lines]) if response else "\n".join(lines)
    return LiturgicalReading(reference=reference, text=text)


def parse_liturgy(day: date, payload: dict[str, Any]) -> DailyLiturgy:
    """Converte o JSON bruto da fonte externa para `DailyLiturgy`.

    Função pura (sem rede) de propósito: os testes exercitam o parsing com
    um payload de exemplo gravado, sem precisar de acesso à internet.
    """
    today = payload["today"]
    readings = today["readings"]

    return DailyLiturgy(
        date=day,
        liturgical_color=today.get("color"),
        celebration=_strip_html(today.get("entry_title")) or None,
        first_reading=_parse_reading(readings["first_reading"], "title"),
        psalm=_parse_psalm(readings["psalm"]),
        second_reading=(
            _parse_reading(readings["second_reading"], "title")
            if "second_reading" in readings
            else None
        ),
        # O evangelho não tem a referência (capítulo/versículo) no campo
        # "title" como as outras leituras — só em "head_title".
        gospel=_parse_reading(readings["gospel"], "head_title"),
        source="sagradaliturgia.com.br",
    )


class HttpLiturgyGateway(LiturgyExternalGateway):
    """Implementação real do gateway, via `httpx`.

    Qualquer falha (rede, HTTP 5xx, JSON num formato inesperado) vira
    `LiturgyFetchError` aqui mesmo — o use case não precisa de `try/except`
    porque a exceção já chega pronta para o handler global."""

    async def fetch(self, day: date) -> DailyLiturgy:
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
                response = await client.get(_API_URL, params={"date": day.isoformat()})
                response.raise_for_status()
                payload = response.json()
            return parse_liturgy(day, payload)
        except Exception as exc:
            logger.warning("Falha ao buscar liturgia de %s: %s", day, exc)
            raise LiturgyFetchError() from exc
