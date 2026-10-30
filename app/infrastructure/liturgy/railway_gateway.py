"""Fonte principal da liturgia: `liturgia.up.railway.app`, API aberta de terceiros.

Assim como a fonte secundária (`http_gateway`), não é um serviço oficial da CNBB
nem do Vaticano. Aceita datas futuras, o que permite buscar com antecedência.
"""

from __future__ import annotations

import logging
import re
from datetime import date
from typing import Any

import httpx

from app.domain.liturgy.entities import DailyLiturgy, LiturgicalReading
from app.domain.liturgy.exceptions import LiturgyFetchError
from app.domain.liturgy.gateway import LiturgyExternalGateway

logger = logging.getLogger(__name__)

_API_URL = "https://liturgia.up.railway.app/v2/"
_TIMEOUT_SECONDS = 10.0
_SOURCE = "liturgia.up.railway.app"
_DATE_RE = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")


def _first(readings: dict[str, Any], key: str) -> dict[str, Any] | None:
    """A fonte devolve listas; quando há mais de uma opção, vale a primeira."""
    items = readings.get(key) or []
    return items[0] if items else None


def _reading(raw: dict[str, Any]) -> LiturgicalReading:
    return LiturgicalReading(
        reference=(raw.get("referencia") or "").strip(),
        text=(raw.get("texto") or "").strip(),
    )


def _psalm(raw: dict[str, Any]) -> LiturgicalReading:
    refrain = (raw.get("refrao") or "").strip()
    text = (raw.get("texto") or "").strip()
    return LiturgicalReading(
        reference=(raw.get("referencia") or "").strip(),
        text=f"{refrain}\n{text}" if refrain else text,
    )


def parse_railway_liturgy(day: date, payload: dict[str, Any]) -> DailyLiturgy:
    """Função pura, sem rede, para os testes usarem um exemplo gravado.

    Recusa resposta de outro dia ou sem as leituras: gravar isso no banco exibiria
    leituras erradas até alguém perceber.
    """
    match = _DATE_RE.match(payload.get("data") or "")
    if not match or date(int(match[3]), int(match[2]), int(match[1])) != day:
        raise ValueError(f"A fonte devolveu outra data: {payload.get('data')}")

    readings = payload["leituras"]
    first = _first(readings, "primeiraLeitura")
    psalm = _first(readings, "salmo")
    gospel = _first(readings, "evangelho")
    if not first or not psalm or not gospel:
        raise ValueError("A fonte devolveu a liturgia sem todas as leituras.")

    second = _first(readings, "segundaLeitura")
    return DailyLiturgy(
        date=day,
        liturgical_color=payload.get("cor"),
        celebration=payload.get("liturgia") or None,
        first_reading=_reading(first),
        psalm=_psalm(psalm),
        second_reading=_reading(second) if second else None,
        gospel=_reading(gospel),
        source=_SOURCE,
    )


class RailwayLiturgyGateway(LiturgyExternalGateway):
    async def fetch(self, day: date) -> DailyLiturgy:
        params = {"dia": day.day, "mes": day.month, "ano": day.year}
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
                response = await client.get(_API_URL, params=params)
                response.raise_for_status()
                return parse_railway_liturgy(day, response.json())
        except Exception as exc:
            logger.warning("Falha na fonte %s para %s: %s", _SOURCE, day, exc)
            raise LiturgyFetchError() from exc


class FallbackLiturgyGateway(LiturgyExternalGateway):
    """Tenta as fontes em ordem; só falha se todas falharem."""

    def __init__(self, gateways: list[LiturgyExternalGateway]) -> None:
        self._gateways = gateways

    async def fetch(self, day: date) -> DailyLiturgy:
        for gateway in self._gateways:
            try:
                return await gateway.fetch(day)
            except LiturgyFetchError:
                continue
        logger.error("Todas as fontes de liturgia falharam para %s", day)
        raise LiturgyFetchError()
