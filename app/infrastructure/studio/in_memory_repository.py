"""Repositórios do estúdio em memória, para testes (mesmo comportamento do Postgres)."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from app.domain.studio.entities import NewVideoRequest, Reel, VideoRequest
from app.domain.studio.repository import ReelRepository, VideoRequestRepository


class InMemoryReelRepository(ReelRepository):
    def __init__(self) -> None:
        self.reels: dict[str, Reel] = {}

    async def list(
        self, *, theme: str | None, only_published: bool, limit: int, offset: int
    ) -> tuple[list[Reel], int]:
        found = [
            r
            for r in self.reels.values()
            if (not only_published or r.published)
            and (theme is None or r.theme == theme)
        ]
        found.sort(
            key=lambda r: (r.created_at or datetime.min.replace(tzinfo=UTC), r.slug),
            reverse=True,
        )
        return found[offset : offset + limit], len(found)

    async def get(self, slug: str) -> Reel | None:
        return self.reels.get(slug)

    async def create(self, reel: Reel) -> Reel:
        if reel.slug in self.reels:
            raise KeyError(reel.slug)
        stored = replace(reel, created_at=reel.created_at or datetime.now(UTC))
        self.reels[reel.slug] = stored
        return stored

    async def update(self, slug: str, patch: dict[str, object]) -> Reel | None:
        if slug not in self.reels:
            return None
        self.reels[slug] = replace(self.reels[slug], **patch)  # type: ignore[arg-type]
        return self.reels[slug]

    async def delete(self, slug: str) -> bool:
        return self.reels.pop(slug, None) is not None


class InMemoryVideoRequestRepository(VideoRequestRepository):
    def __init__(self) -> None:
        self.requests: dict[int, VideoRequest] = {}

    async def create(self, request: NewVideoRequest) -> VideoRequest:
        now = datetime.now(UTC)
        new_id = max(self.requests, default=0) + 1
        self.requests[new_id] = VideoRequest(
            id=new_id,
            theme=request.theme,
            question=request.question,
            notes=request.notes,
            format=request.format,
            own_voice=request.own_voice,
            created_at=now,
            updated_at=now,
        )
        return self.requests[new_id]

    async def list_recent(self, limit: int) -> list[VideoRequest]:
        return sorted(self.requests.values(), key=lambda r: r.id, reverse=True)[:limit]

    async def get(self, request_id: int) -> VideoRequest | None:
        return self.requests.get(request_id)

    async def claim_next(self) -> VideoRequest | None:
        waiting = sorted(
            (r for r in self.requests.values() if r.status == "na_fila"),
            key=lambda r: r.id,
        )
        if not waiting:
            return None
        return await self.update(
            waiting[0].id, status="gerando", stage="Começando", progress=0
        )

    async def update(self, request_id: int, **fields: object) -> VideoRequest | None:
        current = self.requests.get(request_id)
        if current is None:
            return None
        for key, value in fields.items():
            setattr(current, key, value)
        current.updated_at = datetime.now(UTC)
        return current
