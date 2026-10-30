"""Contratos HTTP do perfil e do ranking."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from app.domain.profiles.entities import Profile, RankingRow

DisplayName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=40)]
Slug = Annotated[str, StringConstraints(pattern=r"^[a-z0-9-]{1,80}$")]


class ProfileSyncRequest(BaseModel):
    nome: DisplayName


class ProfileUpdateRequest(BaseModel):
    nome: DisplayName
    preferencias: list[Slug] = Field(default_factory=list, max_length=60)
    no_ranking: bool = False


class LessonsRequest(BaseModel):
    licoes: list[Slug] = Field(min_length=1, max_length=200)


class ProfileResponse(BaseModel):
    nome: str
    preferencias: list[str]
    no_ranking: bool
    pontos: int
    licoes: list[str]

    @classmethod
    def from_entity(cls, profile: Profile) -> ProfileResponse:
        return cls(
            nome=profile.display_name,
            preferencias=profile.preferences,
            no_ranking=profile.show_in_ranking,
            pontos=profile.points,
            licoes=profile.completed_lessons,
        )


class RankingRowResponse(BaseModel):
    nome: str
    pontos: int

    @classmethod
    def from_entity(cls, row: RankingRow) -> RankingRowResponse:
        return cls(nome=row.display_name, pontos=row.points)
