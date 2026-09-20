"""Exceções do domínio de liturgia diária — puro Python, sem FastAPI.

`LiturgyFetchError` é levantada pelo gateway (`app.infrastructure.liturgy.
http_gateway`) quando a fonte externa falha — já é um `AppException`, então
o use case não precisa de `try/except` nenhum: a exceção sobe sozinha até o
handler global (`app.interface.exception_handlers`), que já sabe como
respondê-la. Ver `standards/backend.md` (dev-agent) — "exceção viaja até
onde alguém pode agir, não é traduzida em cada camada que atravessa".
"""

from __future__ import annotations

from app.core.exceptions import ServiceUnavailableException


class LiturgyFetchError(ServiceUnavailableException):
    """A fonte externa da liturgia diária falhou (rede, HTTP 5xx, JSON
    malformado) — nunca um 500 cru pro cliente por causa de um terceiro
    fora do ar."""

    def __init__(self) -> None:
        super().__init__(
            message="Não foi possível buscar a liturgia de hoje. Tente novamente em instantes.",
            code="LITURGIA_INDISPONIVEL",
        )
