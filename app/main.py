"""Ponto de entrada da API do acervo católico.

O acervo é carregado no lifespan: se algum arquivo de conteúdo estiver
inválido, a aplicação **não sobe** — é preferível a um endpoint respondendo
500 silenciosamente em produção.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.exceptions import register_exception_handlers
from app.repository import repository
from app.routers import router

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Carrega o acervo na subida e apenas registra a parada."""
    repository.load()
    logger.info(
        "API iniciada",
        extra={
            "environment": settings.environment,
            "total_entradas": repository.total_entries,
        },
    )
    yield
    logger.info("API encerrada")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "API somente-leitura de conteúdo católico curado: santos, papas, "
        "concílios, milagres eucarísticos, doutores da Igreja, catecismo, "
        "crisma, história, Nossa Senhora, livros, orações, pecados, vida "
        "litúrgica, sacramentos, virtudes, mandamentos, a Bíblia (73 livros "
        "do cânon católico), devoções, glossário e calendário litúrgico. "
        "O acervo cobre o essencial da fé, da moral e da prática católica — "
        "não se restringe a um recorte estreito de temas — e segue sendo "
        "expandido; não é ainda um catálogo definitivo."
    ),
    lifespan=lifespan,
)

# Sem credenciais e sem curinga: o frontend só precisa de GET público.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(router)
