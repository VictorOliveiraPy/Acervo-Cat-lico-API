"""Entidades do perfil de quem estuda na Academia da Fé.

Quem identifica a pessoa é o `sub` do Google, recebido do site. A API não guarda
e-mail nem foto: nome de exibição, padroeiro, preferências, lições concluídas, textos
favoritos e anotações. O exame de consciência nunca chega aqui: fica só no navegador.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

# Pontos por lição concluída. Só exercícios pontuam: oração, velas e santos não,
# regra aprovada para não gamificar a vida espiritual.
POINTS_PER_LESSON = 10

PATRON_SAINTS = ("francisco", "maria", "jose", "teresinha")
DEFAULT_PATRON = "francisco"

# Teto por pessoa em cada lista: sem ele, uma conta só poderia encher o banco.
MAX_ITEMS_PER_USER = 500


@dataclass(frozen=True)
class Profile:
    display_name: str
    preferences: list[str]
    show_in_ranking: bool
    points: int
    completed_lessons: list[str]
    patron_saint: str = DEFAULT_PATRON


@dataclass(frozen=True)
class RankingRow:
    display_name: str
    points: int


@dataclass(frozen=True)
class Favorite:
    id: int
    kind: str
    text: str
    reference: str
    source_url: str | None
    created_at: datetime


@dataclass(frozen=True)
class Note:
    id: int
    tag: str
    body: str
    lesson: str | None
    created_at: datetime
    updated_at: datetime
