"""Entidades do domínio de liturgia diária — puro Python, sem Pydantic."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class LeituraLiturgica:
    """Uma leitura da Missa (1ª leitura, salmo, 2ª leitura ou evangelho)."""

    referencia: str
    texto: str


@dataclass(frozen=True, slots=True)
class LiturgiaDiaria:
    """Liturgia de um dia: cor, celebração do dia e as leituras da Missa.

    `segunda_leitura` só existe aos domingos e solenidades — nos demais dias
    a Missa tem só duas leituras antes do evangelho.
    """

    data: date
    cor_liturgica: str | None
    celebracao: str | None
    primeira_leitura: LeituraLiturgica
    salmo: LeituraLiturgica
    evangelho: LeituraLiturgica
    fonte: str
    segunda_leitura: LeituraLiturgica | None = None
