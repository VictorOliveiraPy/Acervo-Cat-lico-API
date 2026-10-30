"""Busca a liturgia de hoje e dos próximos dias com antecedência.

Com isso, a página lê do banco e não depende da fonte externa na hora do acesso.
Roda em segundo plano dentro da própria API (`app.main`), sem exigir cron na VPS.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone

from app.domain.liturgy.exceptions import LiturgyFetchError
from app.domain.liturgy.gateway import LiturgyExternalGateway
from app.domain.liturgy.repository import DailyLiturgyRepository

logger = logging.getLogger(__name__)

DAYS_AHEAD = 7
INTERVAL_SECONDS = 6 * 60 * 60
_BRAZIL = timezone(timedelta(hours=-3))


async def prefetch_liturgy(
    repository: DailyLiturgyRepository,
    gateway: LiturgyExternalGateway,
    today: date,
) -> list[date]:
    """Devolve os dias que continuam sem liturgia, para o log poder apontá-los."""
    missing: list[date] = []
    for offset in range(DAYS_AHEAD + 1):
        day = today + timedelta(days=offset)
        if await repository.get_cached(day) is not None:
            continue
        try:
            await repository.save(day, await gateway.fetch(day))
        except LiturgyFetchError:
            missing.append(day)
    return missing


async def prefetch_forever(
    repository: DailyLiturgyRepository,
    gateway: LiturgyExternalGateway,
) -> None:
    while True:
        try:
            today = datetime.now(_BRAZIL).date()
            missing = await prefetch_liturgy(repository, gateway, today)
            if missing:
                logger.error("Liturgia sem dados para: %s", [d.isoformat() for d in missing])
            else:
                logger.info("Liturgia em dia até %s", today + timedelta(days=DAYS_AHEAD))
        except Exception:
            # Falha de banco aqui não pode derrubar a API nem parar as próximas rodadas.
            logger.exception("Falha ao antecipar a liturgia")
        await asyncio.sleep(INTERVAL_SECONDS)
