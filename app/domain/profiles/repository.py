"""Contrato de acesso a dados dos perfis — sem implementação aqui.

`PostgresProfileRepository` é o de produção e `InMemoryProfileRepository` o dos
testes, ambos em `app.infrastructure.profiles`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from app.domain.profiles.entities import (
    ActivityId,
    Favorite,
    Note,
    PatronSaint,
    Profile,
    RankingRow,
)


class ProfileRepository(ABC):
    @abstractmethod
    async def ensure(self, subject: str, display_name: str) -> Profile:
        """Devolve o perfil, criando-o no primeiro acesso; não sobrescreve o nome."""

    @abstractmethod
    async def exists(self, subject: str) -> bool: ...

    @abstractmethod
    async def get(self, subject: str) -> Profile | None: ...

    @abstractmethod
    async def set_patron(self, subject: str, patron_saint: PatronSaint) -> Profile | None: ...

    @abstractmethod
    async def update(
        self,
        subject: str,
        display_name: str,
        preferences: list[str],
        show_in_ranking: bool,
    ) -> Profile | None: ...

    @abstractmethod
    async def complete_lessons(
        self, subject: str, lessons: list[str], day: date
    ) -> Profile | None:
        """Conclui as lições no dia; repetir uma lição não soma pontos de novo."""

    @abstractmethod
    async def complete_activity(
        self, subject: str, activity: ActivityId, day: date, points: int
    ) -> Profile | None:
        """Marca a prática no dia valendo `points` (já com o bônus da sequência);
        marcar de novo no mesmo dia não soma pontos."""

    @abstractmethod
    async def advance_path(self, subject: str, house: int, day: date) -> Profile | None:
        """Registra a casa do Caminho da Santidade concluída no dia (a regra é do domínio)."""

    @abstractmethod
    async def delete(self, subject: str) -> None:
        """Apaga o perfil e, com ele, lições, favoritos e anotações."""

    @abstractmethod
    async def ranking(self, limit: int) -> list[RankingRow]:
        """Só quem optou por aparecer e tem algum ponto, de lição ou de prática."""

    @abstractmethod
    async def list_favorites(self, subject: str) -> list[Favorite]:
        """Só os da própria pessoa, do mais recente para o mais antigo."""

    @abstractmethod
    async def add_favorite(
        self,
        subject: str,
        kind: str,
        text: str,
        reference: str,
        source_url: str | None,
    ) -> Favorite | None:
        """`None` quando a pessoa já chegou ao teto `MAX_ITEMS_PER_USER`."""

    @abstractmethod
    async def delete_favorite(self, subject: str, favorite_id: int) -> bool:
        """`False` se não existe ou é de outra pessoa: as duas respostas são iguais."""

    @abstractmethod
    async def list_notes(self, subject: str) -> list[Note]:
        """Só as da própria pessoa, da mais recente para a mais antiga."""

    @abstractmethod
    async def add_note(
        self,
        subject: str,
        tag: str,
        body: str,
        lesson: str | None,
    ) -> Note | None:
        """`None` quando a pessoa já chegou ao teto `MAX_ITEMS_PER_USER`."""

    @abstractmethod
    async def delete_note(self, subject: str, note_id: int) -> bool:
        """`False` se não existe ou é de outra pessoa: as duas respostas são iguais."""
