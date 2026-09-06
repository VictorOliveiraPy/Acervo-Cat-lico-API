"""Modelos do mural de velas: acender uma vela virtual com nome e intenção.

Separado de `models.py` de propósito — aquele arquivo é o contrato do acervo
somente-leitura (carregado de JSON); este é o único canto da API com escrita
persistida, e mora à parte para que a diferença fique óbvia ao ler o código.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TipoVela(str, Enum):
    """As poucas "skins" de vela que a pessoa pode escolher ao acender —
    devoção (Jesus, um santo), não cor.

    Lista curta e fechada de propósito: a imagem de cada tipo mora no
    frontend (mesmo padrão de `CATEGORY_LABELS` no lado do site), então
    adicionar um tipo aqui sem adicionar a imagem lá quebra a tela.
    """

    JESUS = "jesus"
    NOSSA_SENHORA = "nossa_senhora"
    APARECIDA = "aparecida"
    SAO_JOSE = "sao_jose"
    ESPIRITO_SANTO = "espirito_santo"
    SAO_JUDAS_TADEU = "sao_judas_tadeu"


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.split())
    return cleaned or None


class VelaCreate(BaseModel):
    """O que a pessoa envia para acender uma vela."""

    model_config = ConfigDict(extra="forbid")

    nome: str = Field(min_length=1, max_length=60)
    intencao: str | None = Field(default=None, max_length=280)
    tipo: TipoVela

    @field_validator("nome", mode="after")
    @classmethod
    def nome_nao_pode_ser_so_espaco(cls, value: str) -> str:
        cleaned = _clean_text(value)
        if not cleaned:
            raise ValueError("Informe um nome.")
        return cleaned

    @field_validator("intencao", mode="after")
    @classmethod
    def intencao_vazia_vira_none(cls, value: str | None) -> str | None:
        return _clean_text(value)


class Vela(BaseModel):
    """Uma vela já acesa, como aparece no mural público."""

    model_config = ConfigDict(extra="forbid")

    id: int
    nome: str
    intencao: str | None
    tipo: TipoVela
    criado_em: datetime


class VelaPage(BaseModel):
    """Página do mural, mais recentes primeiro."""

    model_config = ConfigDict(extra="forbid")

    total: int
    limit: int
    offset: int
    itens: list[Vela]
