"""Ponto de entrada da API do acervo católico.

O acervo é carregado no lifespan: se algum arquivo de conteúdo estiver
inválido, a aplicação **não sobe** — é preferível a um endpoint respondendo
500 silenciosamente em produção.

O mural de velas (`/api/velas`) é a única escrita persistida da API — mora
num Postgres à parte (`DATABASE_URL`), opcional: sem ele configurado, o
acervo de leitura sobe normalmente e só o mural responde 503. A liturgia
diária (`/api/liturgia-diaria`) usa o mesmo Postgres como cache — sem
`DATABASE_URL`, esse endpoint também responde 503, pelo mesmo motivo.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.exceptions import register_exception_handlers
from app.liturgia_repository import PostgresLiturgiaDiariaRepository
from app.liturgia_router import router as liturgia_router
from app.repository import repository
from app.routers import router
from app.velas_repository import PostgresVelasRepository
from app.velas_router import router as velas_router

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Carrega o acervo e, se configurado, abre o pool do mural de velas."""
    repository.load()

    pool: asyncpg.Pool | None = None
    if settings.database_url:
        try:
            pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=5)
            await PostgresVelasRepository.create_schema(pool)
            app.state.velas_repository = PostgresVelasRepository(pool)
            logger.info("Mural de velas conectado")
        except Exception:
            logger.exception("Falha ao conectar o banco do mural de velas")
            app.state.velas_repository = None

        try:
            # Mesmo pool do mural de velas — é só cache de leitura, não
            # precisa de conexão dedicada.
            if pool is not None:
                await PostgresLiturgiaDiariaRepository.create_schema(pool)
                app.state.liturgia_repository = PostgresLiturgiaDiariaRepository(pool)
                logger.info("Liturgia diária conectada")
            else:
                app.state.liturgia_repository = None
        except Exception:
            logger.exception("Falha ao preparar o cache da liturgia diária")
            app.state.liturgia_repository = None
    else:
        app.state.velas_repository = None
        app.state.liturgia_repository = None
        logger.info("DATABASE_URL não configurada — mural de velas e liturgia diária desativados")

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
        "API de conteúdo católico curado em 45 categorias (somente leitura, "
        "com um único recurso de escrita: o mural de velas em /api/velas): "
        "santos, papas, concílios, milagres eucarísticos, doutores da "
        "Igreja, catecismo, crisma, história, Nossa Senhora, livros, "
        "orações, pecados, vida litúrgica, sacramentos, virtudes, "
        "mandamentos, a Bíblia (73 livros do cânon católico), devoções, "
        "glossário, calendário litúrgico, novíssimos, ordens religiosas, "
        "estrutura da Igreja, santuários, documentos do magistério, beatos "
        "e canonização, Igreja no Brasil, sacramentais, apologética, "
        "Jesus Cristo, personagens bíblicos, parábolas, milagres de Jesus, "
        "Terra Santa, Padres da Igreja, heresias e cismas, anjos e "
        "demônios, doutrina social da Igreja, Liturgia das Horas, ritos e "
        "Igrejas orientais católicas, arte sacra e símbolos, direito "
        "canônico, vocações e estados de vida, primeira comunhão e música "
        "sacra. "
        "O acervo cobre o essencial da fé, da moral e da prática católica — "
        "não se restringe a um recorte estreito de temas — e segue sendo "
        "expandido; não é ainda um catálogo definitivo."
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
# `velas_router`/`liturgia_router` primeiro: `/api/velas` e
# `/api/liturgia-diaria` precisam ser resolvidos antes da rota coringa
# `/api/{categoria}` do acervo, senão virariam slug de categoria inexistente.
app.include_router(velas_router)
app.include_router(liturgia_router)
app.include_router(router)
