"""Entidades do domínio de velas — puro Python, sem Pydantic/FastAPI.

Separadas do schema de API (`app.interface.candles.schemas`) de propósito: a
validação de entrada HTTP (limite de caractere, formato de e-mail) é
preocupação de interface, não regra do domínio — a entidade em si só
carrega o dado já validado.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class CandleType(str, Enum):
    """As poucas "skins" de vela que a pessoa pode escolher ao acender —
    devoção (Jesus, um santo), não cor.

    Lista curta e fechada de propósito: a imagem de cada tipo mora no
    frontend (mesmo padrão de `CATEGORY_LABELS` no lado do site), então
    adicionar um tipo aqui sem adicionar a imagem lá quebra a tela.

    Os valores (strings) são o contrato com o frontend/banco — nunca mudam
    mesmo que o nome do membro em inglês mude.
    """

    JESUS = "jesus"
    OUR_LADY = "nossa_senhora"
    APARECIDA = "aparecida"
    SAINT_JOSEPH = "sao_jose"
    HOLY_SPIRIT = "espirito_santo"
    SAINT_JUDE_THADDEUS = "sao_judas_tadeu"
    CARLO_ACUTIS = "carlo_acutis"
    SAINT_AUGUSTINE = "santo_agostinho"
    SAINT_BENEDICT = "sao_bento"
    SAINT_THERESE = "santa_terezinha"
    SAINT_ANTHONY = "santo_antonio"
    SAINT_JOHN_THE_BAPTIST = "sao_joao_batista"


@dataclass(frozen=True, slots=True)
class NewCandle:
    """Dados para acender uma vela — já validados pela interface, antes de
    ganhar `id`/`created_at`.

    `email` é só para o contato do próprio site com quem acendeu: nunca
    vira campo de `Candle` (ver abaixo), nunca é devolvido pela API nem
    aparece no mural.
    """

    name: str
    candle_type: CandleType
    intention: str | None = None
    city: str | None = None
    state: str | None = None
    email: str | None = None


@dataclass(frozen=True, slots=True)
class Candle:
    """Uma vela já acesa, como aparece no mural público.

    De propósito sem `email`: é dado de contato privado, não devolvido pela
    API nem exibido no mural.
    """

    id: int
    name: str
    intention: str | None
    candle_type: CandleType
    city: str | None
    state: str | None
    created_at: datetime
