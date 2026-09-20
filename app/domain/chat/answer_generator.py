"""Contrato de geração de resposta a partir de trechos recuperados — sem
implementação aqui (ver `app.infrastructure.chat.anthropic_answer_generator`).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.chat.entities import ChunkResult


class AnswerGenerator(ABC):
    """Interface que o use case depende — implementação é um detalhe.

    Só é chamada com `chunks` não-vazio — o use case já decidiu que há
    conteúdo relevante o bastante antes de gastar a chamada (ver
    `AnswerQuestionUseCase` e `select_relevant`).
    """

    @abstractmethod
    async def generate(self, question: str, chunks: list[ChunkResult]) -> str: ...
