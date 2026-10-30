"""Contrato de acesso a dados dos perfis — sem implementação aqui.

`PostgresProfileRepository` é o de produção e `InMemoryProfileRepository` o dos
testes, ambos em `app.infrastructure.profiles`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.profiles.entities import Profile, RankingRow


class ProfileRepository(ABC):
    @abstractmethod
    async def ensure(self, subject: str, display_name: str) -> Profile:
        """Devolve o perfil, criando-o no primeiro acesso; não sobrescreve o nome."""

    @abstractmethod
    async def update(
        self,
        subject: str,
        display_name: str,
        preferences: list[str],
        show_in_ranking: bool,
    ) -> Profile | None: ...

    @abstractmethod
    async def complete_lessons(self, subject: str, lessons: list[str]) -> Profile | None:
        """Conclui as lições; repetir uma lição não soma pontos de novo."""

    @abstractmethod
    async def delete(self, subject: str) -> None: ...

    @abstractmethod
    async def ranking(self, limit: int) -> list[RankingRow]:
        """Só quem optou por aparecer, com pelo menos uma lição concluída."""
