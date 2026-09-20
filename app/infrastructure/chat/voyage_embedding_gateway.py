"""Cliente de embeddings (Voyage AI) — o vetor que representa o significado
de um pedaço de texto, usado tanto pra indexar quanto pra buscar.

`input_type` distingue as duas pontas de propósito (a Voyage otimiza o
embedding diferente pra cada uma): documento na indexação, consulta na
busca. Usar o tipo errado não quebra nada, só perde um pouco de precisão —
mas a diferença é de graça, então não tem razão pra deixar passar.
"""

from __future__ import annotations

import voyageai

from app.core.config import settings
from app.core.exceptions import ServiceUnavailableException
from app.domain.chat.embedding_gateway import EmbeddingGateway


class VoyageEmbeddingGateway(EmbeddingGateway):
    """Implementação real, sobre a API da Voyage."""

    def _client(self) -> voyageai.AsyncClient:
        if not settings.voyage_api_key:
            raise ServiceUnavailableException(
                message="O chatbot está temporariamente indisponível.",
                code="CHAT_INDISPONIVEL",
            )
        return voyageai.AsyncClient(api_key=settings.voyage_api_key)

    async def embed_documents(self, textos: list[str]) -> list[list[float]]:
        if not textos:
            return []
        resultado = await self._client().embed(
            texts=textos,
            model=settings.voyage_embedding_model,
            input_type="document",
            output_dimension=settings.voyage_embedding_dimensions,
        )
        # A lib tipa como int|float (o valor sempre vem float da API) — conversão
        # explícita só pra satisfazer o checker, não muda o valor.
        return [[float(x) for x in emb] for emb in resultado.embeddings]

    async def embed_query(self, pergunta: str) -> list[float]:
        resultado = await self._client().embed(
            texts=[pergunta],
            model=settings.voyage_embedding_model,
            input_type="query",
            output_dimension=settings.voyage_embedding_dimensions,
        )
        return [float(x) for x in resultado.embeddings[0]]
