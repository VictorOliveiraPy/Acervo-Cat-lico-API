"""Busca a liturgia de um dia numa fonte externa.

A fonte (`api-liturgia-diaria.vercel.app`, um agregador de terceiros que lê
de sagradaliturgia.com.br) NÃO é um serviço oficial da CNBB nem do
Vaticano — é o serviço aberto mais completo e estável em português que
encontramos; a CNBB não expõe uma API pública própria. Isolado neste módulo
de propósito: trocar de fonte no futuro (se surgir uma oficial) é mudar só
este arquivo — o repositório e a rota não sabem de onde os dados vêm.
"""

from __future__ import annotations

import html
import re
from datetime import date
from typing import Any

import httpx

from app.liturgia_models import LeituraLiturgica, LiturgiaDiaria

_API_URL = "https://api-liturgia-diaria.vercel.app/"
_TIMEOUT_SECONDS = 10.0

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(value: str | None) -> str:
    """Remove tags HTML simples (`<b>`, `<br/>`) e decodifica entidades."""
    if not value:
        return ""
    text = _TAG_RE.sub(" ", value)
    text = html.unescape(text)
    return " ".join(text.split())


def _parse_leitura(raw: dict[str, Any], referencia_key: str) -> LeituraLiturgica:
    referencia = _strip_html(raw.get(referencia_key))
    texto = _strip_html(raw.get("text"))
    return LeituraLiturgica(referencia=referencia, texto=texto)


def _parse_salmo(raw: dict[str, Any]) -> LeituraLiturgica:
    referencia = _strip_html(raw.get("title"))
    resposta = _strip_html(raw.get("response"))
    linhas = [_strip_html(linha) for linha in raw.get("content_psalm", [])]
    texto = "\n".join([resposta, *linhas]) if resposta else "\n".join(linhas)
    return LeituraLiturgica(referencia=referencia, texto=texto)


def parse_liturgia(dia: date, payload: dict[str, Any]) -> LiturgiaDiaria:
    """Converte o JSON bruto da fonte externa para `LiturgiaDiaria`.

    Função pura (sem rede) de propósito: os testes exercitam o parsing com
    um payload de exemplo gravado, sem precisar de acesso à internet.
    """
    hoje = payload["today"]
    leituras = hoje["readings"]

    return LiturgiaDiaria(
        data=dia,
        cor_liturgica=hoje.get("color"),
        celebracao=_strip_html(hoje.get("entry_title")) or None,
        primeira_leitura=_parse_leitura(leituras["first_reading"], "title"),
        salmo=_parse_salmo(leituras["psalm"]),
        segunda_leitura=(
            _parse_leitura(leituras["second_reading"], "title")
            if "second_reading" in leituras
            else None
        ),
        # O evangelho não tem a referência (capítulo/versículo) no campo
        # "title" como as outras leituras — só em "head_title".
        evangelho=_parse_leitura(leituras["gospel"], "head_title"),
        fonte="sagradaliturgia.com.br",
    )


async def fetch_liturgia(dia: date) -> LiturgiaDiaria:
    """Busca e converte a liturgia de `dia` na fonte externa."""
    async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
        response = await client.get(_API_URL, params={"date": dia.isoformat()})
        response.raise_for_status()
        payload = response.json()

    return parse_liturgia(dia, payload)
