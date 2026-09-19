"""Caso de uso: listar o mural de velas, mais recentes primeiro."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.velas.entities import Vela
from app.domain.velas.repository import VelasRepository


@dataclass(frozen=True, slots=True)
class PaginaDeVelas:
    """Resultado paginado — `total` é a contagem inteira, não só a página."""

    itens: list[Vela]
    total: int


class ListarVelasUseCase:
    """Devolve uma página do mural — a ordenação (mais recentes primeiro)
    é responsabilidade do repositório, que sabe como ordenar de forma
    eficiente na fonte de dados real."""

    def __init__(self, repository: VelasRepository) -> None:
        self._repository = repository

    async def execute(self, limit: int, offset: int) -> PaginaDeVelas:
        itens, total = await self._repository.list_page(limit=limit, offset=offset)
        return PaginaDeVelas(itens=itens, total=total)
