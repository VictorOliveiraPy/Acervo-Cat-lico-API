"""Caminho da Santidade: a trilha de casas e a regra de avançar uma por vez."""

from __future__ import annotations

from datetime import date

import pytest

from app.domain.profiles.entities import ACTIVITY_POINTS
from app.domain.profiles.path import (
    HOUSES,
    VIAS,
    PathError,
    _build,
    check_advance,
    house,
    houses_done,
    task_name,
)

HOJE = date(2026, 11, 25)
ONTEM = date(2026, 11, 24)


def test_three_ways_of_twelve_houses() -> None:
    assert [via.id for via in VIAS] == ["purgativa", "iluminativa", "unitiva"]
    assert len(HOUSES) == 36
    assert [h.number for h in HOUSES] == list(range(1, 37))
    for via in VIAS:
        assert len([h for h in HOUSES if h.via == via.id]) == 12


def test_every_task_exists_and_lessons_fit_the_academy() -> None:
    for h in HOUSES:
        if h.kind == "atividade":
            assert h.task in ACTIVITY_POINTS, h
        else:
            assert h.kind == "licao"
    lessons = [h for h in HOUSES if h.kind == "licao"]
    # A Academia tem 13 lições: a trilha nunca pede mais do que existe.
    assert [h.lessons_needed for h in lessons] == list(range(1, len(lessons) + 1))
    assert len(lessons) <= 13


def test_houses_done_counts_only_the_unbroken_start() -> None:
    assert houses_done([]) == 0
    assert houses_done([(1, ONTEM), (2, HOJE)]) == 2
    assert houses_done([(1, ONTEM), (3, HOJE)]) == 1


def _advance(number: int, **kwargs: object) -> object:
    base: dict[str, object] = {
        "steps": [],
        "last_activity_days": {},
        "lessons_count": 0,
        "today": HOJE,
    }
    base.update(kwargs)
    return check_advance(number, **base)  # type: ignore[arg-type]


def test_first_house_needs_its_practice_marked_today() -> None:
    first = house(1)
    assert first.kind == "atividade"
    with pytest.raises(PathError, match="Marque"):
        _advance(1)
    with pytest.raises(PathError, match="Marque"):
        _advance(1, last_activity_days={first.task: ONTEM})
    assert _advance(1, last_activity_days={first.task: HOJE}) == first


def test_only_the_next_house() -> None:
    first = house(1)
    with pytest.raises(PathError, match="casa 1"):
        _advance(2)
    with pytest.raises(PathError, match=r"^Esta casa já foi concluída\.$"):
        _advance(1, steps=[(1, ONTEM)], last_activity_days={first.task: HOJE})
    with pytest.raises(PathError):
        _advance(37)


def test_lesson_house_counts_completed_lessons() -> None:
    lesson = next(h for h in HOUSES if h.kind == "licao")
    before = [(n, ONTEM) for n in range(1, lesson.number)]
    with pytest.raises(PathError, match=r"^Conclua mais uma lição da Academia da Fé para avançar\.$"):
        _advance(lesson.number, steps=before, lessons_count=lesson.lessons_needed - 1)
    assert _advance(lesson.number, steps=before, lessons_count=lesson.lessons_needed) == lesson


def test_one_marked_practice_moves_one_house_only() -> None:
    # Duas casas com a mesma prática no mesmo dia: a mesma marcação não vale duas vezes.
    first = house(1)
    later = next(h for h in HOUSES if h.number > 1 and h.task == first.task)
    steps = [(n, HOJE if n == 1 else ONTEM) for n in range(1, later.number)]
    with pytest.raises(PathError, match=r"^Esta prática já moveu uma casa hoje\. Volte amanhã para seguir\.$"):
        _advance(later.number, steps=steps, last_activity_days={first.task: HOJE})
    steps = [(n, ONTEM) for n in range(1, later.number)]
    assert _advance(later.number, steps=steps, last_activity_days={first.task: HOJE}) == later


def test_house_lookup() -> None:
    assert house(36).via == "unitiva"
    with pytest.raises(PathError):
        house(0)


def test_build_numbers_houses_and_counts_lessons() -> None:
    built = _build()
    assert built == HOUSES
    assert (built[0].number, built[0].kind, built[0].task, built[0].lessons_needed) == (1, "atividade", "oracao_livre", 0)
    assert (built[2].number, built[2].kind, built[2].task, built[2].lessons_needed) == (3, "licao", "licao", 1)
    assert (built[7].kind, built[7].lessons_needed) == ("licao", 2)
    assert (built[35].title, built[35].via, built[35].task) == ("Santidade", "unitiva", "missa")


def test_task_names() -> None:
    assert task_name(house(3)) == "Lição da Academia da Fé"
    assert task_name(house(1)) == "Oração Livre"
