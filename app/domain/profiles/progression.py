"""Nível, título e sequência de dias, vindos do Santo Guardião.

O XP são os próprios pontos do perfil: não há segunda moeda. A curva é a do site do
Santo Guardião (cada nível pede 15% a mais que o anterior), e o multiplicador da
sequência é o da API de lá (×1,5 a partir de 7 dias, ×2 de 30, ×3 de 100).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta

MAX_LEVEL = 100
_BASE_XP = 100
_GROWTH = 1.15

# Nível a partir do qual vale cada título.
LEVEL_TITLES: tuple[tuple[int, str], ...] = (
    (1, "Peregrino Iniciante"),
    (5, "Devoto Fiel"),
    (10, "Servo Dedicado"),
    (15, "Discípulo da Luz"),
    (20, "Guardião da Fé"),
    (25, "Portador da Esperança"),
    (30, "Mensageiro Celestial"),
    (35, "Arauto da Paz"),
    (40, "Cavaleiro da Virtude"),
    (45, "Paladino Sagrado"),
    (50, "Mestre Espiritual"),
    (60, "Profeta da Luz"),
    (70, "Serafim Terreno"),
    (80, "Querubim Iluminado"),
    (90, "Arcanjo Guardião"),
    (100, "Santo Glorificado"),
)

# Dias seguidos a partir dos quais vale cada multiplicador, do maior para o menor.
_STREAK_MULTIPLIERS: tuple[tuple[int, float], ...] = ((100, 3.0), (30, 2.0), (7, 1.5))


def _xp_to_reach(level: int) -> int:
    """XP para sair do nível anterior e chegar a `level`."""
    return int(_BASE_XP * _GROWTH ** (level - 1))


@dataclass(frozen=True)
class LevelInfo:
    level: int
    title: str
    # Estágio visual do santo: 1 até o nível 10, 2 até 25, 3 até 50, 4 depois.
    stage: int
    xp_in_level: int
    # Zero no nível máximo.
    xp_for_next_level: int


def _stage(level: int) -> int:
    if level >= 51:
        return 4
    if level >= 26:
        return 3
    if level >= 11:
        return 2
    return 1


def level_info(points: int) -> LevelInfo:
    level, spent = 1, 0
    while level < MAX_LEVEL and spent + _xp_to_reach(level + 1) <= points:
        spent += _xp_to_reach(level + 1)
        level += 1
    title = next(name for start, name in reversed(LEVEL_TITLES) if level >= start)
    next_level = _xp_to_reach(level + 1) if level < MAX_LEVEL else 0
    return LevelInfo(level, title, _stage(level), points - spent, next_level)


def current_streak(active_days: Iterable[date], today: date) -> int:
    """Dias seguidos até hoje; se hoje ainda não teve nada, conta até ontem."""
    days = set(active_days)
    day = today if today in days else today - timedelta(days=1)
    count = 0
    while day in days:
        count += 1
        day -= timedelta(days=1)
    return count


def longest_streak(active_days: Iterable[date]) -> int:
    best = run = 0
    previous: date | None = None
    for day in sorted(set(active_days)):
        run = run + 1 if previous is not None and day - previous == timedelta(days=1) else 1
        best = max(best, run)
        previous = day
    return best


def streak_multiplier(streak: int) -> float:
    return next((value for start, value in _STREAK_MULTIPLIERS if streak >= start), 1.0)


def todays_multiplier(active_days: Iterable[date], today: date) -> float:
    """O que vale marcar hoje: conta hoje como ativo, porque marcar o torna ativo."""
    return streak_multiplier(current_streak({*active_days, today}, today))


def points_with_bonus(points: int, multiplier: float) -> int:
    return int(points * multiplier)
