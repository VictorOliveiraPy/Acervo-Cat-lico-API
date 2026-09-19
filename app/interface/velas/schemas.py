"""DTOs Pydantic do mural de velas — a validação de entrada HTTP mora aqui,
não na entidade de domínio (`app.domain.velas.entities`).
"""

from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.velas.entities import NovaVela, TipoVela, Vela

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.split())
    return cleaned or None


class VelaCreateRequest(BaseModel):
    """O que a pessoa envia para acender uma vela.

    `email` é só para o contato do próprio site com quem acendeu (nunca é
    devolvido pela API nem aparece no mural — ver `VelaResponse`, que não
    tem esse campo); `cidade`/`estado` são públicos, como no mural do Padre
    Marcelo Rossi que inspirou esta tela.
    """

    model_config = ConfigDict(extra="forbid")

    nome: str = Field(min_length=1, max_length=60)
    intencao: str | None = Field(default=None, max_length=280)
    tipo: TipoVela
    cidade: str | None = Field(default=None, max_length=80)
    estado: str | None = Field(default=None, max_length=80)
    email: str | None = Field(default=None, max_length=254)

    @field_validator("nome", mode="after")
    @classmethod
    def nome_nao_pode_ser_so_espaco(cls, value: str) -> str:
        cleaned = _clean_text(value)
        if not cleaned:
            raise ValueError("Informe um nome.")
        return cleaned

    @field_validator("intencao", "cidade", "estado", mode="after")
    @classmethod
    def campo_opcional_vazio_vira_none(cls, value: str | None) -> str | None:
        return _clean_text(value)

    @field_validator("email", mode="after")
    @classmethod
    def email_formato_basico(cls, value: str | None) -> str | None:
        cleaned = _clean_text(value)
        if cleaned is None:
            return None
        # Checagem propositalmente simples (não é RFC 5322 completo): é
        # contato para o dono do site, não um campo que dispara e-mail
        # automático — não vale a pena uma dependência extra por isto.
        if not _EMAIL_RE.match(cleaned):
            raise ValueError("E-mail em formato inválido.")
        return cleaned

    def to_entity(self) -> NovaVela:
        """Converte o DTO já validado na entidade que os use cases esperam."""
        return NovaVela(
            nome=self.nome,
            intencao=self.intencao,
            tipo=self.tipo,
            cidade=self.cidade,
            estado=self.estado,
            email=self.email,
        )


class VelaResponse(BaseModel):
    """Uma vela já acesa, como aparece no mural público.

    De propósito sem `email`: é dado de contato privado, não devolvido pela
    API nem exibido no mural.
    """

    model_config = ConfigDict(extra="forbid")

    id: int
    nome: str
    intencao: str | None
    tipo: TipoVela
    cidade: str | None
    estado: str | None
    criado_em: datetime

    @classmethod
    def from_entity(cls, vela: Vela) -> VelaResponse:
        return cls(
            id=vela.id,
            nome=vela.nome,
            intencao=vela.intencao,
            tipo=vela.tipo,
            cidade=vela.cidade,
            estado=vela.estado,
            criado_em=vela.criado_em,
        )


class VelaPageResponse(BaseModel):
    """Página do mural, mais recentes primeiro."""

    model_config = ConfigDict(extra="forbid")

    total: int
    limit: int
    offset: int
    itens: list[VelaResponse]
