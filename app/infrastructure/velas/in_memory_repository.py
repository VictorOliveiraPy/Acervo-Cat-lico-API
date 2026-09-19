"""Fake do repositório de velas — mesma interface, sem rede nem Postgres.

Usado nos testes de `application`/`interface`: nenhum precisa de um
Postgres de verdade rodando.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.domain.velas.entities import NovaVela, Vela
from app.domain.velas.repository import VelasRepository


class InMemoryVelasRepository(VelasRepository):
    def __init__(self) -> None:
        self._itens: list[Vela] = []
        self._next_id = 1

    async def create(self, nova_vela: NovaVela) -> Vela:
        vela = Vela(
            id=self._next_id,
            nome=nova_vela.nome,
            intencao=nova_vela.intencao,
            tipo=nova_vela.tipo,
            cidade=nova_vela.cidade,
            estado=nova_vela.estado,
            criado_em=datetime.now(UTC),
        )
        self._itens.insert(0, vela)
        self._next_id += 1
        return vela

    async def list_page(self, limit: int, offset: int) -> tuple[list[Vela], int]:
        total = len(self._itens)
        return self._itens[offset : offset + limit], total
