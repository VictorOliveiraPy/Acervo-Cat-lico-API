"""DTOs Pydantic da liturgia diária — resposta HTTP, não a entidade de domínio.

Os nomes de CAMPO abaixo (`cor_liturgica`, `celebracao`...) continuam em
português de propósito: são as chaves do JSON que o frontend já consome em
produção.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict

from app.domain.liturgy.entities import DailyLiturgy, LiturgicalReading


class LiturgicalReadingResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    referencia: str
    texto: str

    @classmethod
    def from_entity(cls, reading: LiturgicalReading) -> LiturgicalReadingResponse:
        return cls(referencia=reading.reference, texto=reading.text)


class DailyLiturgyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: date
    cor_liturgica: str | None
    celebracao: str | None
    primeira_leitura: LiturgicalReadingResponse
    salmo: LiturgicalReadingResponse
    segunda_leitura: LiturgicalReadingResponse | None = None
    evangelho: LiturgicalReadingResponse
    fonte: str

    @classmethod
    def from_entity(cls, liturgy: DailyLiturgy) -> DailyLiturgyResponse:
        return cls(
            data=liturgy.date,
            cor_liturgica=liturgy.liturgical_color,
            celebracao=liturgy.celebration,
            primeira_leitura=LiturgicalReadingResponse.from_entity(liturgy.first_reading),
            salmo=LiturgicalReadingResponse.from_entity(liturgy.psalm),
            segunda_leitura=(
                LiturgicalReadingResponse.from_entity(liturgy.second_reading)
                if liturgy.second_reading
                else None
            ),
            evangelho=LiturgicalReadingResponse.from_entity(liturgy.gospel),
            fonte=liturgy.source,
        )
