"""Entidades do perfil de quem estuda na Academia da Fé.

Quem identifica a pessoa é o `sub` do Google, recebido do site. A API não guarda
e-mail nem foto: nome de exibição, padroeiro, preferências, lições concluídas, práticas
marcadas por dia, textos favoritos e anotações. O exame de consciência nunca chega aqui: fica só no navegador.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal

# Pontos por lição concluída.
POINTS_PER_LESSON = 10

# Práticas do dia, vindas do Santo Guardião: cada uma pontua uma vez por dia. A antiga
# regra de não pontuar a vida espiritual foi revogada na fusão com o Santo Guardião.
ActivityId = Literal[
    "terco",
    "leitura_biblica",
    "missa",
    "caridade",
    "adoracao",
    "novena",
    "confissao",
    "jejum",
    "oracao_livre",
]


@dataclass(frozen=True)
class Activity:
    id: ActivityId
    name: str
    description: str
    points: int


ACTIVITIES: tuple[Activity, ...] = (
    Activity("terco", "Rezar o Terço", "Complete as 5 dezenas do terço", 15),
    Activity("leitura_biblica", "Leitura Bíblica", "Leia um capítulo da Bíblia", 20),
    Activity("missa", "Participar da Missa", "Participe da Santa Missa", 50),
    Activity("caridade", "Obra de Caridade", "Pratique uma obra de misericórdia", 40),
    Activity("adoracao", "Adoração ao Santíssimo", "Faça adoração eucarística", 35),
    Activity("novena", "Novena do Santo", "Complete um dia da novena", 25),
    Activity("confissao", "Confissão", "Receba o sacramento da reconciliação", 45),
    Activity("jejum", "Jejum", "Pratique o jejum como sacrifício", 30),
    Activity("oracao_livre", "Oração Livre", "Dedique tempo à oração pessoal", 10),
)
ACTIVITY_POINTS: dict[str, int] = {activity.id: activity.points for activity in ACTIVITIES}

# Mesmos ids de `lib/padroeiros.ts` no site. Perfil novo começa sem padroeiro: a
# escolha é o primeiro passo depois de criar a conta.
PatronSaint = Literal[
    "francisco",
    "maria",
    "jose",
    "teresinha",
    "antonio",
    "pedro",
    "bento",
    "miguel",
    "carlo",
    "cecilia",
]

# Teto por pessoa em cada lista: sem ele, uma conta só poderia encher o banco.
MAX_ITEMS_PER_USER = 500


@dataclass(frozen=True)
class Profile:
    display_name: str
    preferences: list[str]
    show_in_ranking: bool
    points: int
    completed_lessons: list[str]
    patron_saint: PatronSaint | None = None
    # Último dia em que cada prática foi marcada; quem decide o que é "hoje" é a rota.
    last_activity_days: dict[str, date] = field(default_factory=dict)
    # Dias (de Brasília) com lição concluída ou prática marcada: base da sequência.
    active_days: frozenset[date] = frozenset()


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
