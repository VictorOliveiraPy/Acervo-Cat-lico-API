"""Entidades do domínio de velas — puro Python, sem Pydantic/FastAPI.

Separadas do schema de API (`app.interface.velas.schemas`) de propósito: a
validação de entrada HTTP (limite de caractere, formato de e-mail) é
preocupação de interface, não regra do domínio — a entidade em si só
carrega o dado já validado.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


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
    CARLO_ACUTIS = "carlo_acutis"
    SANTO_AGOSTINHO = "santo_agostinho"
    SAO_BENTO = "sao_bento"
    SANTA_TEREZINHA = "santa_terezinha"
    SANTO_ANTONIO = "santo_antonio"
    SAO_JOAO_BATISTA = "sao_joao_batista"


@dataclass(frozen=True, slots=True)
class NovaVela:
    """Dados para acender uma vela — já validados pela interface, antes de
    ganhar `id`/`criado_em`.

    `email` é só para o contato do próprio site com quem acendeu: nunca
    vira campo de `Vela` (ver abaixo), nunca é devolvido pela API nem
    aparece no mural.
    """

    nome: str
    tipo: TipoVela
    intencao: str | None = None
    cidade: str | None = None
    estado: str | None = None
    email: str | None = None


@dataclass(frozen=True, slots=True)
class Vela:
    """Uma vela já acesa, como aparece no mural público.

    De propósito sem `email`: é dado de contato privado, não devolvido pela
    API nem exibido no mural.
    """

    id: int
    nome: str
    intencao: str | None
    tipo: TipoVela
    cidade: str | None
    estado: str | None
    criado_em: datetime
