"""DTOs Pydantic da liturgia diária — resposta HTTP, não a entidade de domínio."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict

from app.domain.liturgia.entities import LeituraLiturgica, LiturgiaDiaria


class LeituraLiturgicaResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    referencia: str
    texto: str

    @classmethod
    def from_entity(cls, leitura: LeituraLiturgica) -> LeituraLiturgicaResponse:
        return cls(referencia=leitura.referencia, texto=leitura.texto)


class LiturgiaDiariaResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: date
    cor_liturgica: str | None
    celebracao: str | None
    primeira_leitura: LeituraLiturgicaResponse
    salmo: LeituraLiturgicaResponse
    segunda_leitura: LeituraLiturgicaResponse | None = None
    evangelho: LeituraLiturgicaResponse
    fonte: str

    @classmethod
    def from_entity(cls, liturgia: LiturgiaDiaria) -> LiturgiaDiariaResponse:
        return cls(
            data=liturgia.data,
            cor_liturgica=liturgia.cor_liturgica,
            celebracao=liturgia.celebracao,
            primeira_leitura=LeituraLiturgicaResponse.from_entity(liturgia.primeira_leitura),
            salmo=LeituraLiturgicaResponse.from_entity(liturgia.salmo),
            segunda_leitura=(
                LeituraLiturgicaResponse.from_entity(liturgia.segunda_leitura)
                if liturgia.segunda_leitura
                else None
            ),
            evangelho=LeituraLiturgicaResponse.from_entity(liturgia.evangelho),
            fonte=liturgia.fonte,
        )
