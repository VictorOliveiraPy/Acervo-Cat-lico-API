"""Cliente de embeddings (Voyage AI) — o vetor que representa o significado
de um pedaço de texto, usado tanto pra indexar quanto pra buscar.

`input_type` distingue as duas pontas de propósito (a Voyage otimiza o
embedding diferente pra cada uma): documento na indexação, consulta na
busca. Usar o tipo errado não quebra nada, só perde um pouco de precisão —
mas a diferença é de graça, então não tem razão pra deixar passar.
"""

from __future__ import annotations

import voyageai

from app.config import settings
from app.exceptions import ServiceUnavailableException


def _client() -> voyageai.AsyncClient:
    if not settings.voyage_api_key:
        raise ServiceUnavailableException(
            message="O chatbot está temporariamente indisponível.",
            code="CHAT_INDISPONIVEL",
        )
    return voyageai.AsyncClient(api_key=settings.voyage_api_key)


async def embed_documents(textos: list[str]) -> list[list[float]]:
    """Embeddings para indexação — chamado pelo script de indexação, em lote."""
    if not textos:
        return []
    resultado = await _client().embed(
        texts=textos,
        model=settings.voyage_embedding_model,
        input_type="document",
        output_dimension=settings.voyage_embedding_dimensions,
    )
    # A lib tipa como int|float (o valor sempre vem float da API) — conversão
    # explícita só pra satisfazer o checker, não muda o valor.
    return [[float(x) for x in emb] for emb in resultado.embeddings]


async def embed_query(pergunta: str) -> list[float]:
    """Embedding de uma pergunta de visitante — chamado a cada mensagem do chat."""
    resultado = await _client().embed(
        texts=[pergunta],
        model=settings.voyage_embedding_model,
        input_type="query",
        output_dimension=settings.voyage_embedding_dimensions,
    )
    return [float(x) for x in resultado.embeddings[0]]
