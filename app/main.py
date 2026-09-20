"""Ponto de entrada da API do acervo católico.

O acervo é carregado no lifespan: se algum arquivo de conteúdo estiver
inválido, a aplicação **não sobe** — é preferível a um endpoint respondendo
500 silenciosamente em produção.

O mural de velas (`/api/velas`) é a única escrita persistida da API — mora
num Postgres à parte (`DATABASE_URL`), opcional: sem ele configurado, o
acervo de leitura sobe normalmente e só o mural responde 503. A liturgia
diária (`/api/liturgia-diaria`) usa o mesmo Postgres como cache — sem
`DATABASE_URL`, esse endpoint também responde 503, pelo mesmo motivo. O
chatbot do acervo (`/api/chat`, RAG — ver `app/domain/chat/`,
`app/application/chat/` e `app/infrastructure/chat/`) precisa do mesmo
Postgres mais duas chaves de API (`ANTHROPIC_API_KEY`, `VOYAGE_API_KEY`);
sem qualquer uma das três, responde 503 e o resto da API segue normal.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.infrastructure.acervo.json_repository import repository
from app.infrastructure.acervo.translations import load_translations
from app.infrastructure.candles.postgres_repository import PostgresCandleRepository
from app.infrastructure.chat.postgres_repository import PostgresRagRepository
from app.infrastructure.liturgy.postgres_repository import (
    PostgresDailyLiturgyRepository,
)
from app.interface.acervo.i18n_router import router as i18n_router
from app.interface.acervo.router import router
from app.interface.candles.router import router as candles_router
from app.interface.chat.router import router as chat_router
from app.interface.exception_handlers import register_exception_handlers
from app.interface.liturgy.router import router as liturgy_router

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Carrega o acervo e, se configurado, abre o pool do mural de velas."""
    repository.load()
    load_translations()

    pool: asyncpg.Pool | None = None
    if settings.database_url:
        try:
            pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=5)
            await PostgresCandleRepository.create_schema(pool)
            app.state.candle_repository = PostgresCandleRepository(pool)
            logger.info("Mural de velas conectado")
        except Exception:
            logger.exception("Falha ao conectar o banco do mural de velas")
            app.state.candle_repository = None

        try:
            # Mesmo pool do mural de velas — é só cache de leitura, não
            # precisa de conexão dedicada.
            if pool is not None:
                await PostgresDailyLiturgyRepository.create_schema(pool)
                app.state.liturgy_repository = PostgresDailyLiturgyRepository(pool)
                logger.info("Liturgia diária conectada")
            else:
                app.state.liturgy_repository = None
        except Exception:
            logger.exception("Falha ao preparar o cache da liturgia diária")
            app.state.liturgy_repository = None

        # Chatbot (RAG): além do banco, precisa das duas chaves de API — sem
        # qualquer uma das três, fica desativado (503), não derruba a API.
        if pool is not None and settings.anthropic_api_key and settings.voyage_api_key:
            try:
                await PostgresRagRepository.create_schema(pool)
                app.state.rag_repository = PostgresRagRepository(pool)
                logger.info("Chatbot do acervo conectado")
            except Exception:
                logger.exception("Falha ao preparar o índice do chatbot")
                app.state.rag_repository = None
        else:
            app.state.rag_repository = None
    else:
        app.state.candle_repository = None
        app.state.liturgy_repository = None
        app.state.rag_repository = None
        logger.info("DATABASE_URL não configurada — mural de velas, liturgia diária e chatbot desativados")

    logger.info(
        "API iniciada",
        extra={
            "environment": settings.environment,
            "total_entradas": repository.total_entries,
        },
    )
    yield
    if pool is not None:
        await pool.close()
    logger.info("API encerrada")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "API de conteúdo católico curado em 49 categorias (somente leitura, "
        "com um único recurso de escrita: o mural de velas em /api/velas): "
        "santos, papas, cardeais, concílios, milagres eucarísticos, "
        "doutores da Igreja, catecismo, crisma, história, Nossa Senhora, "
        "livros, orações, pecados, vida litúrgica, sacramentos, virtudes, "
        "mandamentos, a Bíblia (73 livros do cânon católico), devoções, "
        "glossário, calendário litúrgico, novíssimos, ordens religiosas, "
        "estrutura da Igreja, santuários, documentos do magistério, beatos "
        "e canonização, Igreja no Brasil, sacramentais, apologética, "
        "Jesus Cristo, personagens bíblicos, parábolas, milagres de Jesus, "
        "Terra Santa, Padres da Igreja, heresias e cismas, anjos e "
        "demônios, doutrina social da Igreja, Liturgia das Horas, ritos e "
        "Igrejas orientais católicas, arte sacra e símbolos, direito "
        "canônico, vocações e estados de vida, primeira comunhão, música "
        "sacra, missões e evangelização, ciência e fé, e catedrais e "
        "basílicas do mundo. "
        "O acervo cobre o essencial da fé, da moral e da prática católica — "
        "não se restringe a um recorte estreito de temas — e segue sendo "
        "expandido; não é ainda um catálogo definitivo. Traduções "
        "incrementais para outros idiomas (começando pelo espanhol) ficam "
        "em /api/i18n/{lang}/..., aditivas às rotas em português."
    ),
    lifespan=lifespan,
)

# Sem credenciais e sem curinga: POST só existe para acender uma vela, sem
# cookie nem header de autenticação — não precisa de credentials.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

register_exception_handlers(app)
# Útil em desenvolvimento/homologação. Em produção, IMAGE_CDN_BASE_URL aponta
# para o bucket/CDN que recebe o mesmo conteúdo antes do deploy.
app.mount("/img-acervo", StaticFiles(directory="app/static/img-acervo", check_dir=False), name="imagens")
# `candles_router`/`liturgy_router` primeiro: `/api/velas` e
# `/api/liturgia-diaria` e `/api/chat` precisam ser resolvidos antes da rota
# coringa `/api/{categoria}` do acervo, senão virariam slug de categoria
# inexistente.
app.include_router(candles_router)
app.include_router(liturgy_router)
app.include_router(chat_router)
app.include_router(router)
app.include_router(i18n_router)
