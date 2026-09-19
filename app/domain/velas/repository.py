"""Contrato de acesso a dados do mural de velas — sem implementação aqui.

Duas implementações vivem em `app.infrastructure.velas`:
`PostgresVelasRepository` (produção) e `InMemoryVelasRepository` (testes) —
nenhum teste de `application`/`interface` precisa de um Postgres de verdade
rodando.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.velas.entities import NovaVela, Vela


class VelasRepository(ABC):
    """Interface que os use cases dependem — implementação é um detalhe."""

    @abstractmethod
    async def create(self, nova_vela: NovaVela) -> Vela: ...

    @abstractmethod
    async def list_page(self, limit: int, offset: int) -> tuple[list[Vela], int]: ...
