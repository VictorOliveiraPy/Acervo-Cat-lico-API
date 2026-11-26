"""Contratos HTTP do perfil e do ranking."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

from app.domain.profiles.entities import (
    ACTIVITIES,
    ActivityId,
    Favorite,
    Note,
    PatronSaint,
    Profile,
    RankingRow,
)
from app.domain.profiles.path import HOUSES, VIAS, houses_done, task_name
from app.domain.profiles.progression import (
    current_streak,
    level_info,
    longest_streak,
    points_with_bonus,
    todays_multiplier,
)

DisplayName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=40)]
Slug = Annotated[str, StringConstraints(pattern=r"^[a-z0-9-]{1,80}$")]

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


class PathRequest(BaseModel):
    casa: int = Field(ge=1, le=len(HOUSES))


class PathProgressResponse(BaseModel):
    # Casas seguidas desde a primeira; `hoje`, as concluídas hoje (para a festa na tela).
    concluidas: int
    hoje: list[int]


class ViaResponse(BaseModel):
    id: str
    nome: str
    descricao: str


class HouseResponse(BaseModel):
    numero: int
    via: str
    titulo: str
    texto: str
    tipo: Literal["atividade", "licao"]
    tarefa: str
    tarefa_nome: str
    licoes: int


class PathResponse(BaseModel):
    vias: list[ViaResponse]
    casas: list[HouseResponse]

    @classmethod
    def build(cls) -> PathResponse:
        return cls(
            vias=[ViaResponse(id=v.id, nome=v.name, descricao=v.description) for v in VIAS],
            casas=[
                HouseResponse(
                    numero=h.number, via=h.via, titulo=h.title, texto=h.text, tipo=h.kind,
                    tarefa=h.task, tarefa_nome=task_name(h), licoes=h.lessons_needed,
                )
                for h in HOUSES
            ],
        )


class ActivityRequest(BaseModel):
    atividade: ActivityId


class ActivityResponse(BaseModel):
    id: str
    nome: str
    descricao: str
    pontos: int
    # O que marcar hoje vale, já com o bônus da sequência.
    pontos_hoje: int
    feita_hoje: bool


class LevelResponse(BaseModel):
    numero: int
    titulo: str
    estagio: int
    xp_no_nivel: int
    xp_proximo_nivel: int


class StreakResponse(BaseModel):
    atual: int
    recorde: int
    # O que vale marcar uma prática hoje.
    multiplicador: float


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
    padroeiro_id: PatronSaint | None
    atividades: list[ActivityResponse]
    nivel: LevelResponse
    sequencia: StreakResponse
    caminho: PathProgressResponse

    @classmethod
    def from_entity(cls, profile: Profile, today: date) -> ProfileResponse:
        level = level_info(profile.points)
        multiplier = todays_multiplier(profile.active_days, today)
        return cls(
            nome=profile.display_name,
            preferencias=profile.preferences,
            no_ranking=profile.show_in_ranking,
            pontos=profile.points,
            licoes=profile.completed_lessons,
            padroeiro_id=profile.patron_saint,
            atividades=[
                ActivityResponse(
                    id=activity.id,
                    nome=activity.name,
                    descricao=activity.description,
                    pontos=activity.points,
                    pontos_hoje=points_with_bonus(activity.points, multiplier),
                    feita_hoje=profile.last_activity_days.get(activity.id) == today,
                )
                for activity in ACTIVITIES
            ],
            nivel=LevelResponse(
                numero=level.level,
                titulo=level.title,
                estagio=level.stage,
                xp_no_nivel=level.xp_in_level,
                xp_proximo_nivel=level.xp_for_next_level,
            ),
            sequencia=StreakResponse(
                atual=current_streak(profile.active_days, today),
                recorde=longest_streak(profile.active_days),
                multiplicador=multiplier,
            ),
            caminho=PathProgressResponse(
                concluidas=houses_done(profile.path_steps),
                hoje=[number for number, day in profile.path_steps if day == today],
            ),
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
