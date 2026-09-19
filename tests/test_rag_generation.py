"""Testes de `app/rag/generation.py` — a parte que decide se/como chama o Claude."""

from __future__ import annotations

import pytest

import app.rag.generation as generation_module
from app.core.exceptions import ServiceUnavailableException
from app.rag.generation import (
    NO_MATCH_MESSAGE,
    SIMILARITY_THRESHOLD,
    generate_answer,
    select_relevant,
)
from app.rag.models import ChunkResult


def _chunk(similaridade: float) -> ChunkResult:
    return ChunkResult(
        fonte_tipo="acervo",
        fonte_ref="santos/francisco-de-assis",
        titulo="São Francisco de Assis",
        texto="Fundador da Ordem dos Frades Menores.",
        similaridade=similaridade,
    )


def test_should_keep_only_chunks_at_or_above_the_threshold() -> None:
    # Given
    trechos = [_chunk(0.9), _chunk(SIMILARITY_THRESHOLD), _chunk(0.1)]

    # When
    relevantes = select_relevant(trechos)

    # Then
    assert len(relevantes) == 2
    assert all(t.similaridade >= SIMILARITY_THRESHOLD for t in relevantes)


async def test_should_refuse_without_calling_the_api_when_no_relevant_chunk() -> None:
    """Garantia isolada: trechos vazios nunca chegam a exigir
    `ANTHROPIC_API_KEY` nem tocar rede — o guard-rail central do chatbot."""
    # Given / When
    resposta = await generate_answer("Qual a capital da França?", [])

    # Then
    assert resposta == NO_MATCH_MESSAGE


async def test_should_fail_as_service_unavailable_when_api_key_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Com trecho relevante mas sem chave configurada, 503 — não uma exceção
    genérica nem uma tentativa de responder mesmo assim."""
    # Given
    monkeypatch.setattr(generation_module.settings, "anthropic_api_key", None)

    # When / Then
    with pytest.raises(ServiceUnavailableException) as exc_info:
        await generate_answer("Quem fundou os franciscanos?", [_chunk(0.9)])

    assert exc_info.value.code == "CHAT_INDISPONIVEL"
