"""Contrato de acesso ao índice de embeddings do chatbot (`rag_chunks`)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.chat.entities import ChunkInput, ChunkResult


class RagRepository(ABC):
    """Interface que o use case depende — implementação é um detalhe."""

    @abstractmethod
    async def replace_source(
        self,
        source_type: str,
        source_ref: str,
        chunks: list[ChunkInput],
        embeddings: list[list[float]],
    ) -> None:
        """Substitui todos os chunks de uma fonte (usado ao reindexar)."""

    @abstractmethod
    async def search(self, embedding: list[float], limit: int) -> list[ChunkResult]:
        """Os `limit` chunks mais parecidos com `embedding`, mais parecido primeiro."""
