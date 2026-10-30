"""Repositório de perfis em memória, para os testes não dependerem de um Postgres."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.domain.profiles.entities import (
    DEFAULT_PATRON,
    MAX_ITEMS_PER_USER,
    POINTS_PER_LESSON,
    Favorite,
    Note,
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
    patron_saint: str = DEFAULT_PATRON
    favorites: list[Favorite] = field(default_factory=list)
    notes: list[Note] = field(default_factory=list)


class InMemoryProfileRepository(ProfileRepository):
    def __init__(self) -> None:
        self._rows: dict[str, _Row] = {}
        self._next_id = 0

    @staticmethod
    def _to_profile(row: _Row) -> Profile:
        return Profile(
            display_name=row.display_name,
            preferences=list(row.preferences),
            show_in_ranking=row.show_in_ranking,
            points=len(row.lessons) * POINTS_PER_LESSON,
            completed_lessons=list(row.lessons),
            patron_saint=row.patron_saint,
        )

    async def ensure(self, subject: str, display_name: str) -> Profile:
        row = self._rows.setdefault(subject, _Row(display_name=display_name))
        return self._to_profile(row)

    async def exists(self, subject: str) -> bool:
        return subject in self._rows

    async def set_patron(self, subject: str, patron_saint: str) -> Profile | None:
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
