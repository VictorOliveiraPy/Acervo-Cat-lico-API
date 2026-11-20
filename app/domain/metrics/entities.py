"""Entidades das métricas de visitas."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

HitKind = Literal["pagina", "evento"]
Device = Literal["celular", "computador"]


@dataclass(frozen=True)
class NewHit:
    """Uma visita a uma página ou um evento (vela acesa, busca...)."""

    day: date
    kind: HitKind
    path: str
    event: str | None
    # Só o domínio de quem mandou a visita (google.com), nunca a URL inteira.
    referrer: str | None
    device: Device
    # Hash curto que muda todo dia: conta pessoas no dia sem identificar ninguém.
    visitor: str


@dataclass(frozen=True)
class DayCount:
    day: date
    visitors: int
    views: int


@dataclass(frozen=True)
class Ranked:
    name: str
    count: int


@dataclass(frozen=True)
class MetricsSummary:
    start: date
    end: date
    days: list[DayCount]
    visitors: int
    views: int
    previous_visitors: int
    previous_views: int
    top_pages: list[Ranked]
    top_referrers: list[Ranked]
    events: list[Ranked]
    devices: list[Ranked]
