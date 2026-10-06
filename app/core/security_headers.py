"""Middleware de cabeçalhos de segurança — cross-cutting, camada de core.

A API serve só JSON (e as imagens estáticas em `/img-acervo`), então o
conjunto de cabeçalhos é o mínimo que faz sentido para uma superfície sem
sessão e sem HTML: nada de clickjacking, nada de MIME sniffing, nada de
vazar a URL de origem no `Referer`. HSTS só é enviado quando o deploy é
HTTPS — mandar HSTS em desenvolvimento local, que serve HTTP puro, faria o
navegador forçar HTTPS em `localhost` e quebrar o ambiente.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# Dois anos, com subdomínios: é o valor que a própria recomendação do HSTS
# usa como piso para produção. Só entra quando a conexão já é HTTPS.
_HSTS_VALUE = "max-age=63072000; includeSubDomains"

_BASE_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adiciona cabeçalhos de segurança a toda resposta, HTTPS ou não."""

    def __init__(self, app: object, *, enable_hsts: bool = False) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._enable_hsts = enable_hsts

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Chama o próximo handler e acrescenta os cabeçalhos na saída."""
        response = await call_next(request)
        for header, value in _BASE_HEADERS.items():
            response.headers.setdefault(header, value)
        # HSTS é fixado pelo navegador por um bom tempo: só em produção, onde
        # o Render serve tudo por HTTPS.
        if self._enable_hsts:
            response.headers.setdefault("Strict-Transport-Security", _HSTS_VALUE)
        return response
