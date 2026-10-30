"""Entidades do perfil de quem estuda na Academia da Fé.

Quem identifica a pessoa é o `sub` do Google, recebido do site. A API não guarda
e-mail nem foto: nome de exibição, preferências e lições concluídas bastam para o
perfil e o ranking.
"""

from __future__ import annotations

from dataclasses import dataclass

# Pontos por lição concluída. Só exercícios pontuam: oração, velas e santos não,
# regra aprovada para não gamificar a vida espiritual.
POINTS_PER_LESSON = 10


@dataclass(frozen=True)
class Profile:
    display_name: str
    preferences: list[str]
    show_in_ranking: bool
    points: int
    completed_lessons: list[str]


@dataclass(frozen=True)
class RankingRow:
    display_name: str
    points: int
