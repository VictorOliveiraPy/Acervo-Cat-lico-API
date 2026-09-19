"""Limite de frequência de escrita por IP — cross-cutting, não pertence a
nenhum domínio específico. Usado hoje por `interface.velas.router` e
`chat_router`; cada um cria sua própria instância de `RateLimiter` com a
janela que fizer sentido pro endpoint.
"""

from __future__ import annotations

import time

from fastapi import Request

from app.core.exceptions import RateLimitedException


class RateLimiter:
    """Guarda o horário do último acesso por IP, em memória do processo.

    Em memória porque um processo só (Render free) não precisa de Redis
    para uma defesa simples contra flood grosseiro de bot — não é uma
    defesa séria contra abuso coordenado.
    """

    def __init__(self, window_seconds: float) -> None:
        self._window = window_seconds
        self._last_seen: dict[str, float] = {}

    def check(self, client_ip: str) -> None:
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
