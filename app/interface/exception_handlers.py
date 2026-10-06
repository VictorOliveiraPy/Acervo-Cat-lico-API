"""Handlers HTTP das exceções de domínio — camada de interface (FastAPI).

Separado de `app.core.exceptions` de propósito: as classes de exceção são
puro Python (domain/application/infrastructure importam sem trazer
FastAPI junto); só este módulo, que converte exceção em `JSONResponse`,
tem motivo pra importar FastAPI.

Todo erro que sai daqui — inclusive os que o FastAPI levantaria sozinho —
usa o **mesmo contrato** `{code, message, details}`. Um frontend que já
ramifica em `code` não precisa de um segundo caminho pra tratar `422` de
validação ou `404/405` do Starlette.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppException, DataIntegrityError

logger = logging.getLogger(__name__)


def _error_body(code: str, message: str, details: dict | None = None) -> dict:
    """Monta o corpo de erro no contrato único `{code, message, details}`."""
    return {"code": code, "message": message, "details": details or {}}


def register_exception_handlers(app: FastAPI) -> None:
    """Registra os handlers que convertem exceção de domínio em resposta HTTP."""

    @app.exception_handler(AppException)
    async def handle_app_exception(
        request: Request, exc: AppException
    ) -> JSONResponse:
        """Erro esperado de negócio: responde com o código de contrato."""
        logger.info(
            "Requisição rejeitada por regra de domínio",
            extra={
                "code": exc.code,
                "status_code": exc.status_code,
                "path": request.url.path,
            },
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Entrada inválida (Pydantic/query/path): 422 no mesmo contrato.

        Sem este handler o FastAPI devolveria `{"detail": [...]}` — um
        segundo formato de erro que o frontend teria que conhecer. Aqui os
        erros do Pydantic entram em `details.errors`, mantendo `code` e
        `message` como o resto da API. Os valores recebidos (`input`) são
        omitidos de propósito: o corpo pode carregar dado sensível, e o log
        do servidor já basta para depurar.
        """
        errors = [
            {
                "loc": list(error.get("loc", ())),
                "msg": error.get("msg", ""),
                "type": error.get("type", ""),
            }
            for error in exc.errors()
        ]
        logger.info(
            "Requisição rejeitada por validação de entrada",
            extra={"path": request.url.path, "errors": errors},
        )
        return JSONResponse(
            status_code=422,
            content=_error_body(
                "validation_error",
                "Um ou mais campos da requisição são inválidos.",
                {"errors": errors},
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        """404/405/etc. do Starlette normalizados no mesmo contrato.

        Também cobre `HTTPException` do FastAPI (que herda da do Starlette):
        uma rota que levante `HTTPException` direto ainda responde no formato
        `{code, message, details}` em vez de `{"detail": "..."}`.
        """
        logger.info(
            "Requisição encerrada com erro HTTP",
            extra={"path": request.url.path, "status_code": exc.status_code},
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(_code_for_status(exc.status_code), str(exc.detail)),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(DataIntegrityError)
    async def handle_data_integrity_error(
        request: Request, exc: DataIntegrityError
    ) -> JSONResponse:
        """Integridade de conteúdo: loga o detalhe, responde genérico.

        `DataIntegrityError` normalmente derruba o boot (ver
        `infrastructure/acervo/json_repository`), mas se uma instância chegar
        a vazar para dentro de uma requisição o cliente **não** pode ver a
        mensagem crua — ela cita nome de arquivo, campo, slug ou (num domínio
        com banco) nome de constraint/tabela. O detalhe completo fica só no
        log do servidor.
        """
        logger.exception(
            "Falha de integridade de conteúdo",
            extra={"path": request.url.path, "detail": str(exc)},
        )
        return JSONResponse(
            status_code=500,
            content=_error_body(
                "INTERNAL_ERROR",
                "Erro interno ao processar a requisição.",
            ),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Falha inesperada: loga com contexto e responde sem vazar detalhes."""
        logger.exception(
            "Erro inesperado ao processar requisição",
            extra={"path": request.url.path, "error_type": type(exc).__name__},
        )
        return JSONResponse(
            status_code=500,
            content=_error_body(
                "INTERNAL_ERROR",
                "Erro interno ao processar a requisição.",
            ),
        )


# Códigos estáveis para os erros que o próprio Starlette levanta antes de
# chegar a um handler de domínio. O frontend ramifica em `code`, não em texto.
_STATUS_CODES: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    413: "PAYLOAD_TOO_LARGE",
    429: "RATE_LIMITED",
}


def _code_for_status(status_code: int) -> str:
    """Mapeia um status HTTP do Starlette para o `code` estável do contrato."""
    return _STATUS_CODES.get(status_code, f"HTTP_{status_code}")
