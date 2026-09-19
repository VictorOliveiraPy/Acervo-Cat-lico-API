"""Caso de uso: acender uma vela no mural público."""

from __future__ import annotations

from app.domain.velas.entities import NovaVela, Vela
from app.domain.velas.repository import VelasRepository


class AcenderVelaUseCase:
    """Orquestra a criação de uma vela — hoje é uma passagem direta ao
    repositório, mas é aqui (não no router) que uma regra de negócio nova
    sobre acender uma vela entraria."""

    def __init__(self, repository: VelasRepository) -> None:
        self._repository = repository

    async def execute(self, nova_vela: NovaVela) -> Vela:
        return await self._repository.create(nova_vela)
