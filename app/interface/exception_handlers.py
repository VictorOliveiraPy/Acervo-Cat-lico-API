"""Handlers HTTP das exceções de domínio — camada de interface (FastAPI).

Separado de `app.core.exceptions` de propósito: as classes de exceção são
puro Python (domain/application/infrastructure importam sem trazer
FastAPI junto); só este módulo, que converte exceção em `JSONResponse`,
tem motivo pra importar FastAPI.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import AppException

logger = logging.getLogger(__name__)


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
            content={
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
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
            content={
                "code": "INTERNAL_ERROR",
                "message": "Erro interno ao processar a requisição.",
                "details": {},
            },
        )
