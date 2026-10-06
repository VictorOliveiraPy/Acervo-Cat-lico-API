"""Limite de frequência de escrita por IP — cross-cutting, não pertence a
nenhum domínio específico. Usado hoje por `interface.velas.router` e
`chat_router`; cada um cria sua própria instância de `RateLimiter` com a
janela que fizer sentido pro endpoint.

**Limite de memória do processo, e isso importa.** O contador vive num
`dict` em memória: com mais de um worker (ou mais de uma instância no
Render), cada processo tem o seu próprio contador, então o limite efetivo
é `janela × número_de_processos` — não é um limite global. É defesa contra
flood grosseiro de um único bot, não contra abuso coordenado. Para um
limite de verdade multi-worker é preciso um backend compartilhado (Redis);
enquanto não houver um, `RATE_LIMIT_ENABLED` dá o jeito de desligar o
limite via configuração em vez de deixá-lo dando falsa sensação de
segurança — um endpoint que se apoia nele para proteger recurso caro (o
chat, por exemplo) precisa saber que ele não segura tráfego distribuído.
"""

from __future__ import annotations

import time

from fastapi import Request

from app.core.config import settings
from app.core.exceptions import RateLimitedException


class RateLimiter:
    """Guarda o horário do último acesso por IP, em memória do processo.

    Em memória porque um processo só (Render free) não precisa de Redis
    para uma defesa simples contra flood grosseiro de bot — não é uma
    defesa séria contra abuso coordenado (ver o docstring do módulo).
    """

    def __init__(self, window_seconds: float, *, enabled: bool = True) -> None:
        self._window = window_seconds
        self._enabled = enabled
        self._last_seen: dict[str, float] = {}

    def check(self, client_ip: str) -> None:
        """Levanta `RateLimitedException` se o IP pediu de novo dentro da janela."""
        if not self._enabled:
            return
        now = time.monotonic()
        last = self._last_seen.get(client_ip)
        if last is not None and (now - last) < self._window:
            wait = round(self._window - (now - last))
            raise RateLimitedException(
                message=f"Espere {wait}s antes de tentar novamente.",
                details={"retry_after_seconds": wait},
            )
        self._last_seen[client_ip] = now


def client_ip(request: Request) -> str:
    """IP do cliente, respeitando o proxy do Render (`X-Forwarded-For`)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "desconhecido"


def build_rate_limiter(window_seconds: float) -> RateLimiter:
    """Cria um `RateLimiter` respeitando `settings.rate_limit_enabled`.

    Ponto único de construção: os routers não decidem se o limite vale, só
    a configuração — assim desligá-lo em ambiente controlado (testes de
    carga, homologação) é uma variável de ambiente, não uma edição de código.
    """
    return RateLimiter(window_seconds, enabled=settings.rate_limit_enabled)
