"""Regra de domínio: o que conta como "relevante o bastante pra responder".

Pura (sem I/O) de propósito — decide sem depender de rede, banco ou SDK
nenhum, então é testável isolada e reaproveitável por qualquer use case.
"""

from __future__ import annotations

from app.domain.chat.entities import ChunkResult

# Abaixo disto, o trecho mais parecido ainda está longe demais da pergunta
# pra valer a pena gastar uma chamada ao modelo — melhor recusar direto.
# Calibrado empiricamente; ajuste depois de ver perguntas reais chegarem.
SIMILARITY_THRESHOLD = 0.5

NO_MATCH_MESSAGE = (
    "Não encontrei isso no acervo do Compêndio Católico. Tente reformular a "
    "pergunta, ou use a busca do site pra explorar por tema."
)


def select_relevant(chunks: list[ChunkResult]) -> list[ChunkResult]:
    """Filtra os trechos recuperados pelos que são parecidos o bastante pra usar."""
    return [chunk for chunk in chunks if chunk.similarity >= SIMILARITY_THRESHOLD]
