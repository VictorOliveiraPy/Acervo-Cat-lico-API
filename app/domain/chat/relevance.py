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

# Sinal fixo que o próprio modelo devolve (ver SYSTEM_PROMPT em
# deepseek_answer_generator.py, regra 2) quando os trechos passaram no
# filtro de similaridade acima mas nenhum responde de verdade à pergunta —
# ex.: pergunta sobre "o padre" recupera trechos sobre catequista/família/
# mandamentos (similares o bastante pra valer a chamada ao modelo, mas não
# uma resposta). `AnswerQuestionUseCase` troca esse marcador por
# NO_MATCH_MESSAGE e esvazia as fontes — bug real corrigido: o visitante via
# os títulos desses trechos citados como "fonte" de uma resposta que o
# próprio texto admitia não responder à pergunta, e a explicação
# improvisada pelo modelo sobre o motivo variava e às vezes soava
# incoerente (ex.: uma busca por uma palavra válida e completa descrita
# como "parece incompleta").
INSUFFICIENT_CONTEXT_MARKER = "SEM_TRECHO_SUFICIENTE"


def select_relevant(chunks: list[ChunkResult]) -> list[ChunkResult]:
    """Filtra os trechos recuperados pelos que são parecidos o bastante pra usar."""
    return [chunk for chunk in chunks if chunk.similarity >= SIMILARITY_THRESHOLD]
