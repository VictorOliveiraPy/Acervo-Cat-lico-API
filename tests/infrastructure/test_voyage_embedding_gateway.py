"""Testes de `VoyageEmbeddingGateway` — o SDK é substituído por um fake,
nenhum teste chama a API da Voyage de verdade."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

import app.infrastructure.chat.voyage_embedding_gateway as gateway_module
from app.domain.chat.exceptions import EmbeddingGenerationError
from app.infrastructure.chat.voyage_embedding_gateway import VoyageEmbeddingGateway


@dataclass
class _FakeEmbedResult:
    embeddings: list[list[float]]


class _FakeAsyncClient:
    def __init__(self, api_key: str, should_fail: bool = False) -> None:
        self._should_fail = should_fail

    async def embed(self, **kwargs: object) -> _FakeEmbedResult:
        if self._should_fail:
            raise RuntimeError("Voyage fora do ar")
        texts = kwargs["texts"]
        return _FakeEmbedResult(embeddings=[[1.0, 0.0, 0.0] for _ in texts])  # type: ignore[union-attr]


async def test_should_embed_query_with_the_configured_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    monkeypatch.setattr(gateway_module.settings, "voyage_api_key", "fake")
    monkeypatch.setattr(
        gateway_module.voyageai, "AsyncClient", lambda api_key: _FakeAsyncClient(api_key)
    )
    gateway = VoyageEmbeddingGateway()

    # When
    embedding = await gateway.embed_query("O que é a Crisma?")

    # Then
    assert embedding == [1.0, 0.0, 0.0]


async def test_should_raise_embedding_generation_error_when_sdk_call_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """O gateway traduz qualquer falha do SDK — quem chama não precisa de
    `try/except` porque a exceção já chega pronta pro handler global."""
    # Given
    monkeypatch.setattr(gateway_module.settings, "voyage_api_key", "fake")
    monkeypatch.setattr(
        gateway_module.voyageai,
        "AsyncClient",
        lambda api_key: _FakeAsyncClient(api_key, should_fail=True),
    )
    gateway = VoyageEmbeddingGateway()

    # When / Then
    with pytest.raises(EmbeddingGenerationError):
        await gateway.embed_query("Qualquer pergunta")


async def test_should_raise_embedding_generation_error_without_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(gateway_module.settings, "voyage_api_key", "")
    gateway = VoyageEmbeddingGateway()

    with pytest.raises(EmbeddingGenerationError):
        await gateway.embed_query("Qualquer pergunta")
