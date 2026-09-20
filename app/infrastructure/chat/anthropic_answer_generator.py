"""Monta o prompt e chama o Claude — a única parte do pipeline que "escreve".

Regra de ouro do módulo: o modelo só vê os trechos recuperados do acervo, e a
instrução deixa isso explícito. Nada aqui pede pro modelo "complementar com o
que sabe" — é exatamente o oposto do que essa peça existe pra evitar.
"""

from __future__ import annotations

import anthropic

from app.core.config import settings
from app.core.exceptions import ServiceUnavailableException
from app.domain.chat.answer_generator import AnswerGenerator
from app.domain.chat.entities import ChunkResult

SYSTEM_PROMPT = """Você é o assistente de busca do Compêndio Católico, um catálogo de referência sobre fé, doutrina e vida católica.

Regras que você nunca quebra:
1. Responda SOMENTE com base nos trechos do acervo fornecidos abaixo. Nunca complete com conhecimento próprio, mesmo que pareça óbvio ou que você "tenha certeza".
2. Se os trechos fornecidos não contiverem informação suficiente para responder à pergunta, diga isso claramente ("não encontrei isso no acervo" ou equivalente) em vez de arriscar uma resposta incompleta ou inventada.
3. Nunca invente número de parágrafo do Catecismo, cânone de direito canônico, data ou citação que não esteja literalmente presente nos trechos fornecidos.
4. Quando os trechos forem suficientes, responda de forma direta e sóbria, no tom de uma obra de referência — sem triunfalismo, sem ironia com outras confissões cristãs, sem linguagem de combate.
5. Responda em português.

Você não é um teólogo nem uma autoridade da Igreja — é um assistente de busca sobre um catálogo específico. Não emita juízo doutrinal além do que os trechos já dizem."""


def _montar_contexto(trechos: list[ChunkResult]) -> str:
    return "\n\n---\n\n".join(f"[{t.titulo}]\n{t.texto}" for t in trechos)


class AnthropicAnswerGenerator(AnswerGenerator):
    """Implementação real, sobre a API do Claude."""

    async def generate(self, pergunta: str, trechos: list[ChunkResult]) -> str:
        """Assume `trechos` não-vazio — ver `AnswerGenerator`."""
        if not settings.anthropic_api_key:
            raise ServiceUnavailableException(
                message="O chatbot está temporariamente indisponível.",
                code="CHAT_INDISPONIVEL",
            )

        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        contexto = _montar_contexto(trechos)
        response = await client.messages.create(
            model=settings.chat_model,
            max_tokens=800,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Trechos do acervo:\n\n{contexto}\n\n"
                        f"Pergunta do visitante: {pergunta}"
                    ),
                }
            ],
        )

        return "".join(
            block.text for block in response.content if block.type == "text"
        ).strip()
