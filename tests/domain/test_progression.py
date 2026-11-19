"""Nível, título e sequência de dias, vindos do Santo Guardião."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.domain.profiles.progression import (
    MAX_LEVEL,
    current_streak,
    level_info,
    longest_streak,
    points_with_bonus,
    streak_multiplier,
)

TODAY = date(2026, 11, 15)


def _days(*offsets: int) -> frozenset[date]:
    return frozenset(TODAY - timedelta(days=offset) for offset in offsets)


def test_should_start_at_level_one_as_a_beginner() -> None:
    info = level_info(0)
    assert (info.level, info.title, info.stage) == (1, "Peregrino Iniciante", 1)
    assert (info.xp_in_level, info.xp_for_next_level) == (0, 114)


def test_should_grow_each_level_by_fifteen_percent() -> None:
    # 100 × 1,15 em ponto flutuante dá 114,99…: 114, como o `Math.floor` do site de lá.
    assert level_info(113).level == 1
    second = level_info(114)
    assert (second.level, second.xp_in_level, second.xp_for_next_level) == (2, 0, 132)
    assert level_info(114 + 132).level == 3


def test_should_change_title_and_stage_with_the_level() -> None:
    assert level_info(572).title == "Devoto Fiel"  # nível 5
    assert level_info(1926).title == "Servo Dedicado"  # nível 10
    assert level_info(1926).stage == 1
    assert level_info(10_136).stage == 2  # nível 20


def test_should_stop_at_the_max_level() -> None:
    info = level_info(10**12)
    assert info.level == MAX_LEVEL
    assert info.title == "Santo Glorificado"
    assert info.stage == 4
    assert info.xp_for_next_level == 0


@pytest.mark.parametrize(
    ("days", "expected"),
    [
        (_days(), 0),
        (_days(0), 1),
        (_days(1), 1),  # ontem ainda vale: o dia de hoje não acabou
        (_days(2), 0),
        (_days(0, 1, 2), 3),
        (_days(1, 2, 3), 3),
        (_days(0, 1, 3, 4, 5), 2),
    ],
)
def test_should_count_consecutive_days_ending_today_or_yesterday(
    days: frozenset[date], expected: int
) -> None:
    assert current_streak(days, TODAY) == expected


def test_should_remember_the_longest_streak() -> None:
    assert longest_streak(_days()) == 0
    assert longest_streak(_days(0, 1, 5, 6, 7, 8, 20)) == 4


@pytest.mark.parametrize(
    ("streak", "multiplier"),
    [(0, 1.0), (6, 1.0), (7, 1.5), (29, 1.5), (30, 2.0), (99, 2.0), (100, 3.0)],
)
def test_should_multiply_points_by_streak(streak: int, multiplier: float) -> None:
    assert streak_multiplier(streak) == multiplier


def test_should_round_bonus_points_down() -> None:
    assert points_with_bonus(15, 1.5) == 22
    assert points_with_bonus(50, 2.0) == 100


def _first_points_of(level: int) -> int:
    """Menor pontuação que já está no nível, achada pela própria `level_info`."""
    low, high = 0, 10**9
    while low < high:
        middle = (low + high) // 2
        if level_info(middle).level >= level:
            high = middle
        else:
            low = middle + 1
    return low


@pytest.mark.parametrize(
    ("last_level", "stage_before", "stage_after"),
    [(10, 1, 2), (25, 2, 3), (50, 3, 4)],
)
def test_should_change_the_saint_stage_exactly_after_levels_10_25_and_50(
    last_level: int, stage_before: int, stage_after: int
) -> None:
    first_of_next = _first_points_of(last_level + 1)
    before = level_info(first_of_next - 1)
    after = level_info(first_of_next)
    assert (before.level, before.stage) == (last_level, stage_before)
    assert (after.level, after.stage) == (last_level + 1, stage_after)
