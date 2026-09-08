"""Modelos da liturgia diária: leituras da Missa do dia.

Separado de `models.py` pelo mesmo motivo de `velas_models.py`: não é
conteúdo do acervo (curado à mão, versionado em JSON), é conteúdo vivo que
muda todo dia e vem de fora — busca-se numa fonte externa e cacheia-se em
banco (ver `liturgia_client.py` e `liturgia_repository.py`).
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict


class LeituraLiturgica(BaseModel):
    """Uma leitura da Missa (1ª leitura, salmo, 2ª leitura ou evangelho)."""

    model_config = ConfigDict(extra="forbid")

    referencia: str
    texto: str


class LiturgiaDiaria(BaseModel):
    """Liturgia de um dia: cor, celebração do dia e as leituras da Missa.

    `segunda_leitura` só existe aos domingos e solenidades — nos demais dias
    a Missa tem só duas leituras antes do evangelho.
    """

    model_config = ConfigDict(extra="forbid")

    data: date
    cor_liturgica: str | None
    celebracao: str | None
    primeira_leitura: LeituraLiturgica
    salmo: LeituraLiturgica
    segunda_leitura: LeituraLiturgica | None = None
    evangelho: LeituraLiturgica
    fonte: str
