"""Entidades do domínio de liturgia diária — puro Python, sem Pydantic."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class LiturgicalReading:
    """Uma leitura da Missa (1ª leitura, salmo, 2ª leitura ou evangelho)."""

    reference: str
    text: str


@dataclass(frozen=True, slots=True)
class DailyLiturgy:
    """Liturgia de um dia: cor, celebração do dia e as leituras da Missa.

    `second_reading` só existe aos domingos e solenidades — nos demais dias
    a Missa tem só duas leituras antes do evangelho.
    """

    date: date
    liturgical_color: str | None
    celebration: str | None
    first_reading: LiturgicalReading
    psalm: LiturgicalReading
    gospel: LiturgicalReading
    source: str
    second_reading: LiturgicalReading | None = None
