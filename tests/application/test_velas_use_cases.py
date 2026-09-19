"""Testes dos use cases de velas isolados da camada HTTP — nenhum destes
sobe um `TestClient` nem conhece FastAPI, só o repositório fake."""

from __future__ import annotations

from app.application.velas.acender_vela_use_case import AcenderVelaUseCase
from app.application.velas.listar_velas_use_case import ListarVelasUseCase
from app.domain.velas.entities import NovaVela, TipoVela
from app.infrastructure.velas.in_memory_repository import InMemoryVelasRepository


async def test_should_return_created_vela_with_assigned_id() -> None:
    # Given
    repo = InMemoryVelasRepository()
    use_case = AcenderVelaUseCase(repo)
    nova_vela = NovaVela(nome="Maria", tipo=TipoVela.JESUS, intencao="Por todos")

    # When
    vela = await use_case.execute(nova_vela)

    # Then
    assert vela.id == 1
    assert vela.nome == "Maria"
    assert vela.intencao == "Por todos"


async def test_should_list_page_with_total_count_when_more_items_than_limit() -> None:
    # Given
    repo = InMemoryVelasRepository()
    acender = AcenderVelaUseCase(repo)
    for nome in ["Primeira", "Segunda", "Terceira"]:
        await acender.execute(NovaVela(nome=nome, tipo=TipoVela.SAO_BENTO))

    # When
    pagina = await ListarVelasUseCase(repo).execute(limit=2, offset=0)

    # Then
    assert pagina.total == 3
    assert [vela.nome for vela in pagina.itens] == ["Terceira", "Segunda"]
