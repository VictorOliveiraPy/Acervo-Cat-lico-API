"""Cliente de embeddings (Voyage AI) — o vetor que representa o significado
de um pedaço de texto, usado tanto pra indexar quanto pra buscar.

`input_type` distingue as duas pontas de propósito (a Voyage otimiza o
embedding diferente pra cada uma): documento na indexação, consulta na
busca. Usar o tipo errado não quebra nada, só perde um pouco de precisão —
mas a diferença é de graça, então não tem razão pra deixar passar.

Qualquer falha (sem chave, rede, HTTP 5xx da Voyage) vira
`EmbeddingGenerationError` aqui mesmo — quem chama este gateway não precisa
de `try/except` porque a exceção já chega pronta para o handler global.
"""

from __future__ import annotations

import logging

import voyageai

from app.core.config import settings
from app.domain.chat.embedding_gateway import EmbeddingGateway
from app.domain.chat.exceptions import EmbeddingGenerationError

logger = logging.getLogger(__name__)


class VoyageEmbeddingGateway(EmbeddingGateway):
    """Implementação real, sobre a API da Voyage."""

    def _client(self) -> voyageai.AsyncClient:
        if not settings.voyage_api_key:
            raise EmbeddingGenerationError()
        return voyageai.AsyncClient(api_key=settings.voyage_api_key)

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            result = await self._client().embed(
                texts=texts,
                model=settings.voyage_embedding_model,
                input_type="document",
                output_dimension=settings.voyage_embedding_dimensions,
            )
        except EmbeddingGenerationError:
            raise
        except Exception as exc:
            logger.exception("Falha ao gerar embeddings de documentos")
            raise EmbeddingGenerationError() from exc
        # A lib tipa como int|float (o valor sempre vem float da API) — conversão
        # explícita só pra satisfazer o checker, não muda o valor.
        return [[float(x) for x in emb] for emb in result.embeddings]

    async def embed_query(self, question: str) -> list[float]:
        try:
            result = await self._client().embed(
                texts=[question],
                model=settings.voyage_embedding_model,
                input_type="query",
                output_dimension=settings.voyage_embedding_dimensions,
            )
        except EmbeddingGenerationError:
            raise
        except Exception as exc:
            logger.exception("Falha ao gerar embedding da pergunta")
            raise EmbeddingGenerationError() from exc
        return [float(x) for x in result.embeddings[0]]
