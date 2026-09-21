"""Ponto único de criação do cliente do provedor de LLM do chatbot.

Todo o resto da infraestrutura (`deepseek_answer_generator`) fala com o
provedor por aqui — trocar de provedor (DeepSeek hoje, outro amanhã) é mexer
só neste arquivo, desde que a API seja compatível com o formato OpenAI.

Usamos o SDK `openai` apontado para a base_url da DeepSeek: ela expõe uma API
compatível com `chat/completions` do OpenAI, então o mesmo SDK serve — é a
integração recomendada pela própria DeepSeek. A chave e a base_url vêm de
`Settings` (`DEEPSEEK_API_KEY` / `DEEPSEEK_BASE_URL`), nunca de `os.getenv`
espalhado.
"""

from __future__ import annotations

from openai import AsyncOpenAI

from app.core.config import settings
from app.domain.chat.exceptions import AnswerGenerationError


def get_llm_client() -> AsyncOpenAI:
    """Monta um client assíncrono apontado para a DeepSeek.

    Sem `DEEPSEEK_API_KEY` configurada, levanta `AnswerGenerationError` na
    hora — mesma convenção dos outros gateways: quem chama não precisa de
    `try/except`, a exceção já chega pronta pro handler global.

    Uma instância por chamada é aceitável (o `AsyncOpenAI` só guarda a
    config, não abre conexão na construção); não vale manter um singleton
    global só por isso.
    """
    if not settings.deepseek_api_key:
        raise AnswerGenerationError()
    return AsyncOpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
    )
