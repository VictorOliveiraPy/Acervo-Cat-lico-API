"""Exceções de domínio e seus handlers HTTP.

O repositório levanta exceção de domínio; quem traduz para HTTP é o handler
registrado no `main`. Assim a regra de negócio não conhece FastAPI, e o `code`
(string estável) fica sendo o contrato com o frontend — a `message` é UX e pode
mudar; o `code` não muda sem aviso.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppException(Exception):
    """Base das exceções de domínio, já com status HTTP e código estável."""

    def __init__(
        self,
        message: str,
        status_code: int,
        code: str,
        details: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details or {}


class NotFoundException(AppException):
    """Recurso inexistente."""

    def __init__(
        self,
        message: str = "Recurso não encontrado.",
        code: str = "NOT_FOUND",
        details: dict | None = None,
    ) -> None:
        super().__init__(message, status_code=404, code=code, details=details)


class CategoryNotFoundException(NotFoundException):
    """Categoria fora do conjunto conhecido do acervo."""

    def __init__(self, categoria: str) -> None:
        super().__init__(
            message=f"Categoria '{categoria}' não existe no acervo.",
            code="CATEGORY_NOT_FOUND",
            details={"categoria": categoria},
        )


class EntryNotFoundException(NotFoundException):
    """Entrada inexistente dentro de uma categoria existente."""

    def __init__(self, categoria: str, slug: str) -> None:
        super().__init__(
            message=f"Nenhuma entrada '{slug}' na categoria '{categoria}'.",
            code="ENTRY_NOT_FOUND",
            details={"categoria": categoria, "slug": slug},
        )


class ServiceUnavailableException(AppException):
    """Recurso opcional (ex.: mural de velas) sem o backend configurado."""

    def __init__(
        self,
        message: str = "Serviço temporariamente indisponível.",
        code: str = "SERVICE_UNAVAILABLE",
        details: dict | None = None,
    ) -> None:
        super().__init__(message, status_code=503, code=code, details=details)


class RateLimitedException(AppException):
    """Cliente excedeu a frequência permitida de escrita."""

    def __init__(
        self,
        message: str = "Aguarde um momento antes de tentar novamente.",
        code: str = "RATE_LIMITED",
        details: dict | None = None,
    ) -> None:
        super().__init__(message, status_code=429, code=code, details=details)


class DataIntegrityError(ValueError):
    """Conteúdo do acervo inválido — derruba o boot, nunca é ignorado.

    Herda de `ValueError` porque é, de fato, dado malformado: mantém a
    semântica da `ValidationError` do Pydantic que costuma originá-la.
    """


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
