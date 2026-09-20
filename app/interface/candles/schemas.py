"""DTOs Pydantic do mural de velas — a validação de entrada HTTP mora aqui,
não na entidade de domínio (`app.domain.candles.entities`).

Os nomes de CAMPO abaixo (`nome`, `tipo`, `cidade`...) continuam em
português de propósito: viram as chaves do JSON que o frontend já consome
em produção — mudar aqui quebraria o contrato HTTP publicado. Só nomes de
classe/método (que não aparecem no JSON) são ingleses.
"""

from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.candles.entities import Candle, CandleType, NewCandle

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.split())
    return cleaned or None


class CandleCreateRequest(BaseModel):
    """O que a pessoa envia para acender uma vela.

    `email` é só para o contato do próprio site com quem acendeu (nunca é
    devolvido pela API nem aparece no mural — ver `CandleResponse`, que não
    tem esse campo); `cidade`/`estado` são públicos, como no mural do Padre
    Marcelo Rossi que inspirou esta tela.
    """

    model_config = ConfigDict(extra="forbid")

    nome: str = Field(min_length=1, max_length=60)
    intencao: str | None = Field(default=None, max_length=280)
    tipo: CandleType
    cidade: str | None = Field(default=None, max_length=80)
    estado: str | None = Field(default=None, max_length=80)
    email: str | None = Field(default=None, max_length=254)

    @field_validator("nome", mode="after")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        cleaned = _clean_text(value)
        if not cleaned:
            raise ValueError("Informe um nome.")
        return cleaned

    @field_validator("intencao", "cidade", "estado", mode="after")
    @classmethod
    def blank_optional_field_becomes_none(cls, value: str | None) -> str | None:
        return _clean_text(value)

    @field_validator("email", mode="after")
    @classmethod
    def email_basic_format(cls, value: str | None) -> str | None:
        cleaned = _clean_text(value)
        if cleaned is None:
            return None
        # Checagem propositalmente simples (não é RFC 5322 completo): é
        # contato para o dono do site, não um campo que dispara e-mail
        # automático — não vale a pena uma dependência extra por isto.
        if not _EMAIL_RE.match(cleaned):
            raise ValueError("E-mail em formato inválido.")
        return cleaned

    def to_entity(self) -> NewCandle:
        """Converte o DTO já validado na entidade que os use cases esperam."""
        return NewCandle(
            name=self.nome,
            intention=self.intencao,
            candle_type=self.tipo,
            city=self.cidade,
            state=self.estado,
            email=self.email,
        )


class CandleResponse(BaseModel):
    """Uma vela já acesa, como aparece no mural público.

    De propósito sem `email`: é dado de contato privado, não devolvido pela
    API nem exibido no mural.
    """

    model_config = ConfigDict(extra="forbid")

    id: int
    nome: str
    intencao: str | None
    tipo: CandleType
    cidade: str | None
    estado: str | None
    criado_em: datetime

    @classmethod
    def from_entity(cls, candle: Candle) -> CandleResponse:
        return cls(
            id=candle.id,
            nome=candle.name,
            intencao=candle.intention,
            tipo=candle.candle_type,
            cidade=candle.city,
            estado=candle.state,
            criado_em=candle.created_at,
        )


class CandlePageResponse(BaseModel):
    """Página do mural, mais recentes primeiro."""

    model_config = ConfigDict(extra="forbid")

    total: int
    limit: int
    offset: int
    itens: list[CandleResponse]
