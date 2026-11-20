"""Contratos de dados do estúdio; implementações em `app.infrastructure.studio`."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.studio.entities import NewVideoRequest, Reel, VideoRequest


class ReelRepository(ABC):
    @abstractmethod
    async def list(
        self, *, theme: str | None, only_published: bool, limit: int, offset: int
    ) -> tuple[list[Reel], int]: ...

    @abstractmethod
    async def get(self, slug: str) -> Reel | None: ...

    @abstractmethod
    async def create(self, reel: Reel) -> Reel:
        """Grava; se o slug já existe, levanta `KeyError`."""

    @abstractmethod
    async def update(self, slug: str, patch: dict[str, object]) -> Reel | None: ...

    @abstractmethod
    async def delete(self, slug: str) -> bool: ...


class VideoRequestRepository(ABC):
    @abstractmethod
    async def create(self, request: NewVideoRequest) -> VideoRequest: ...

    @abstractmethod
    async def list_recent(self, limit: int) -> list[VideoRequest]: ...

    @abstractmethod
    async def get(self, request_id: int) -> VideoRequest | None: ...

    @abstractmethod
    async def claim_next(self) -> VideoRequest | None:
        """O pedido mais antigo na fila passa para `gerando` e é devolvido, ou `None`."""

    @abstractmethod
    async def update(
        self, request_id: int, **fields: object
    ) -> VideoRequest | None: ...
