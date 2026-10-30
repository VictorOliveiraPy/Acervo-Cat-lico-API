"""Contratos HTTP do perfil e do ranking."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

from app.domain.profiles.entities import Favorite, Note, Profile, RankingRow

DisplayName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=40)]
Slug = Annotated[str, StringConstraints(pattern=r"^[a-z0-9-]{1,80}$")]

PatronSaint = Literal["francisco", "maria", "jose", "teresinha"]
FavoriteKind = Literal["Bíblia", "Catecismo", "Oração", "Santos"]
NoteTag = Literal["Lição", "Leitura do dia", "Homilia", "Oração", "Dúvida para o padre"]
LongText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
Reference = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]
# Só caminho interno do site: a página transforma isto em link, e `javascript:` ou um
# domínio externo guardados aqui virariam um link perigoso.
SitePath = Annotated[str, StringConstraints(pattern=r"^/(?:[^/\s\\][^\s\\]{0,298})?$")]


class ProfileSyncRequest(BaseModel):
    nome: DisplayName


class ProfileUpdateRequest(BaseModel):
    nome: DisplayName
    preferencias: list[Slug] = Field(default_factory=list, max_length=60)
    no_ranking: bool = False


class LessonsRequest(BaseModel):
    licoes: list[Slug] = Field(min_length=1, max_length=200)


class PatronRequest(BaseModel):
    padroeiro_id: PatronSaint


class FavoriteRequest(BaseModel):
    tipo: FavoriteKind
    texto: LongText
    referencia: Reference = ""
    url_origem: SitePath | None = None


class NoteRequest(BaseModel):
    categoria: NoteTag
    texto: LongText
    licao: Slug | None = None


class ProfileResponse(BaseModel):
    nome: str
    preferencias: list[str]
    no_ranking: bool
    pontos: int
    licoes: list[str]
    padroeiro_id: str

    @classmethod
    def from_entity(cls, profile: Profile) -> ProfileResponse:
        return cls(
            nome=profile.display_name,
            preferencias=profile.preferences,
            no_ranking=profile.show_in_ranking,
            pontos=profile.points,
            licoes=profile.completed_lessons,
            padroeiro_id=profile.patron_saint,
        )


class RankingRowResponse(BaseModel):
    nome: str
    pontos: int

    @classmethod
    def from_entity(cls, row: RankingRow) -> RankingRowResponse:
        return cls(nome=row.display_name, pontos=row.points)


class FavoriteResponse(BaseModel):
    id: int
    tipo: str
    texto: str
    referencia: str
    url_origem: str | None
    criado_em: datetime

    @classmethod
    def from_entity(cls, favorite: Favorite) -> FavoriteResponse:
        return cls(
            id=favorite.id,
            tipo=favorite.kind,
            texto=favorite.text,
            referencia=favorite.reference,
            url_origem=favorite.source_url,
            criado_em=favorite.created_at,
        )


class NoteResponse(BaseModel):
    id: int
    categoria: str
    texto: str
    licao: str | None
    criado_em: datetime
    atualizado_em: datetime

    @classmethod
    def from_entity(cls, note: Note) -> NoteResponse:
        return cls(
            id=note.id,
            categoria=note.tag,
            texto=note.body,
            licao=note.lesson,
            criado_em=note.created_at,
            atualizado_em=note.updated_at,
        )
