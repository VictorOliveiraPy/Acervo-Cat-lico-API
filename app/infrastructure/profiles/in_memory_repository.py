"""Repositório de perfis em memória, para os testes não dependerem de um Postgres."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.profiles.entities import POINTS_PER_LESSON, Profile, RankingRow
from app.domain.profiles.repository import ProfileRepository


@dataclass
class _Row:
    display_name: str
    preferences: list[str] = field(default_factory=list)
    show_in_ranking: bool = False
    lessons: list[str] = field(default_factory=list)


class InMemoryProfileRepository(ProfileRepository):
    def __init__(self) -> None:
        self._rows: dict[str, _Row] = {}

    @staticmethod
    def _to_profile(row: _Row) -> Profile:
        return Profile(
            display_name=row.display_name,
            preferences=list(row.preferences),
            show_in_ranking=row.show_in_ranking,
            points=len(row.lessons) * POINTS_PER_LESSON,
            completed_lessons=list(row.lessons),
        )

    async def ensure(self, subject: str, display_name: str) -> Profile:
        row = self._rows.setdefault(subject, _Row(display_name=display_name))
        return self._to_profile(row)

    async def update(
        self,
        subject: str,
        display_name: str,
        preferences: list[str],
        show_in_ranking: bool,
    ) -> Profile | None:
        row = self._rows.get(subject)
        if row is None:
            return None
        row.display_name = display_name
        row.preferences = preferences
        row.show_in_ranking = show_in_ranking
        return self._to_profile(row)

    async def complete_lessons(self, subject: str, lessons: list[str]) -> Profile | None:
        row = self._rows.get(subject)
        if row is None:
            return None
        for lesson in lessons:
            if lesson not in row.lessons:
                row.lessons.append(lesson)
        return self._to_profile(row)

    async def delete(self, subject: str) -> None:
        self._rows.pop(subject, None)

    async def ranking(self, limit: int) -> list[RankingRow]:
        rows = [
            RankingRow(row.display_name, len(row.lessons) * POINTS_PER_LESSON)
            for row in self._rows.values()
            if row.show_in_ranking and row.lessons
        ]
        rows.sort(key=lambda row: (-row.points, row.display_name))
        return rows[:limit]
