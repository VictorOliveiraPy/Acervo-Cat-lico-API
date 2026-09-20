"""Contrato de geração de embeddings — sem implementação aqui.

A implementação real (`app.infrastructure.chat.voyage_embedding_gateway`)
sabe qual provedor/modelo usa; o domínio só conhece "dado um texto, devolva
o vetor que o representa".
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingGateway(ABC):
    """Interface que use cases dependem — implementação é um detalhe."""

    @abstractmethod
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embeddings para indexação, em lote — usado pelo script de indexação."""

    @abstractmethod
    async def embed_query(self, question: str) -> list[float]:
        """Embedding de uma pergunta de visitante — usado a cada mensagem do chat."""
