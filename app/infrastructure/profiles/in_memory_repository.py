"""Repositório de perfis em memória, para os testes não dependerem de um Postgres."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from app.domain.profiles.entities import (
    MAX_ITEMS_PER_USER,
    POINTS_PER_LESSON,
    ActivityId,
    Favorite,
    Note,
    PatronSaint,
    Profile,
    RankingRow,
)
from app.domain.profiles.repository import ProfileRepository


@dataclass
class _Row:
    display_name: str
    preferences: list[str] = field(default_factory=list)
    show_in_ranking: bool = False
    lessons: list[str] = field(default_factory=list)
    lesson_days: list[date] = field(default_factory=list)
    patron_saint: PatronSaint | None = None
    # (prática, dia) -> pontos ganhos naquele dia.
    activities: dict[tuple[str, date], int] = field(default_factory=dict)
    favorites: list[Favorite] = field(default_factory=list)
    notes: list[Note] = field(default_factory=list)
    path_steps: dict[int, date] = field(default_factory=dict)


class InMemoryProfileRepository(ProfileRepository):
    def __init__(self) -> None:
        self._rows: dict[str, _Row] = {}
        self._next_id = 0

    @staticmethod
    def _points(row: _Row) -> int:
        return len(row.lessons) * POINTS_PER_LESSON + sum(row.activities.values())

    @staticmethod
    def _to_profile(row: _Row) -> Profile:
        last_days: dict[str, date] = {}
        for activity, day in sorted(row.activities, key=lambda key: key[1]):
            last_days[activity] = day
        return Profile(
            display_name=row.display_name,
            preferences=list(row.preferences),
            show_in_ranking=row.show_in_ranking,
            points=InMemoryProfileRepository._points(row),
            completed_lessons=list(row.lessons),
            patron_saint=row.patron_saint,
            last_activity_days=last_days,
            active_days=frozenset(row.lesson_days)
            | frozenset(day for _, day in row.activities),
            path_steps=tuple(sorted(row.path_steps.items())),
        )

    async def ensure(self, subject: str, display_name: str) -> Profile:
        row = self._rows.setdefault(subject, _Row(display_name=display_name))
        return self._to_profile(row)

    async def exists(self, subject: str) -> bool:
        return subject in self._rows

    async def get(self, subject: str) -> Profile | None:
        row = self._rows.get(subject)
        return self._to_profile(row) if row else None

    async def set_patron(self, subject: str, patron_saint: PatronSaint) -> Profile | None:
        row = self._rows.get(subject)
        if row is None:
            return None
        row.patron_saint = patron_saint
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

    async def complete_lessons(
        self, subject: str, lessons: list[str], day: date
    ) -> Profile | None:
        row = self._rows.get(subject)
        if row is None:
            return None
        for lesson in lessons:
            if lesson not in row.lessons:
                row.lessons.append(lesson)
                row.lesson_days.append(day)
        return self._to_profile(row)

    async def complete_activity(
        self, subject: str, activity: ActivityId, day: date, points: int
    ) -> Profile | None:
        row = self._rows.get(subject)
        if row is None:
            return None
        row.activities.setdefault((activity, day), points)
        return self._to_profile(row)

    async def advance_path(self, subject: str, house: int, day: date) -> Profile | None:
        row = self._rows.get(subject)
        if row is None:
            return None
        row.path_steps.setdefault(house, day)
        return self._to_profile(row)

    async def delete(self, subject: str) -> None:
        self._rows.pop(subject, None)

    async def ranking(self, limit: int) -> list[RankingRow]:
        rows = [
            RankingRow(row.display_name, self._points(row))
            for row in self._rows.values()
            if row.show_in_ranking and self._points(row) > 0
        ]
        rows.sort(key=lambda row: (-row.points, row.display_name))
        return rows[:limit]

    def _new_id(self) -> int:
        self._next_id += 1
        return self._next_id

    async def list_favorites(self, subject: str) -> list[Favorite]:
        row = self._rows.get(subject)
        return list(reversed(row.favorites)) if row else []

    async def add_favorite(
        self,
        subject: str,
        kind: str,
        text: str,
        reference: str,
        source_url: str | None,
    ) -> Favorite | None:
        row = self._rows[subject]
        if len(row.favorites) >= MAX_ITEMS_PER_USER:
            return None
        favorite = Favorite(
            self._new_id(), kind, text, reference, source_url, datetime.now(UTC)
        )
        row.favorites.append(favorite)
        return favorite

    async def delete_favorite(self, subject: str, favorite_id: int) -> bool:
        row = self._rows.get(subject)
        if row is None or not any(item.id == favorite_id for item in row.favorites):
            return False
        row.favorites = [item for item in row.favorites if item.id != favorite_id]
        return True

    async def list_notes(self, subject: str) -> list[Note]:
        row = self._rows.get(subject)
        return list(reversed(row.notes)) if row else []

    async def add_note(
        self,
        subject: str,
        tag: str,
        body: str,
        lesson: str | None,
    ) -> Note | None:
        row = self._rows[subject]
        if len(row.notes) >= MAX_ITEMS_PER_USER:
            return None
        now = datetime.now(UTC)
        note = Note(self._new_id(), tag, body, lesson, now, now)
        row.notes.append(note)
        return note

    async def delete_note(self, subject: str, note_id: int) -> bool:
        row = self._rows.get(subject)
        if row is None or not any(item.id == note_id for item in row.notes):
            return False
        row.notes = [item for item in row.notes if item.id != note_id]
        return True
