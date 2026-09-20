"""Testes de `app/application/chat/chunking.py` — sem rede, sem banco."""

from __future__ import annotations

import pytest

from app.application.chat.chunking import chunk_entry, split_paragraphs
from app.infrastructure.acervo.json_repository import Repository


def test_should_split_on_blank_lines_and_collapse_internal_breaks() -> None:
    """Mesmo comportamento de `paragraphs()` no frontend: parágrafo é bloco
    separado por linha em branco; quebra de linha dentro do bloco vira espaço."""
    # Given
    corpo = "Primeiro parágrafo,\ncom quebra no meio.\n\nSegundo parágrafo."

    # When
    partes = split_paragraphs(corpo)

    # Then
    assert partes == [
        "Primeiro parágrafo, com quebra no meio.",
        "Segundo parágrafo.",
    ]


def test_should_drop_empty_blocks_from_extra_blank_lines() -> None:
    # Given
    corpo = "Um.\n\n\n\nDois."

    # When
    partes = split_paragraphs(corpo)

    # Then
    assert partes == ["Um.", "Dois."]


def test_should_return_single_block_when_corpo_has_no_blank_line() -> None:
    # Given / When
    partes = split_paragraphs("Só um parágrafo, sem quebra dupla.")

    # Then
    assert partes == ["Só um parágrafo, sem quebra dupla."]


@pytest.fixture(scope="module")
def repository() -> Repository:
    repo = Repository()
    repo.load()
    return repo


def test_should_chunk_a_real_entry_into_resumo_plus_one_chunk_per_paragraph(
    repository: Repository,
) -> None:
    """Verbete real (Francisco de Assis) — resumo + N parágrafos do corpo."""
    # Given
    entry = repository.get_by_slug("santos", "francisco-de-assis")

    # When
    chunks = chunk_entry(entry)

    # Then
    esperado = 1 + len(split_paragraphs(entry.corpo))
    assert len(chunks) == esperado
    assert chunks[0].texto == entry.resumo
    assert all(chunk.fonte_tipo == "acervo" for chunk in chunks)
    assert all(chunk.fonte_ref == "santos/francisco-de-assis" for chunk in chunks)
    assert all(chunk.titulo == entry.titulo for chunk in chunks)


def test_should_never_produce_empty_chunk_text(repository: Repository) -> None:
    """Nenhum chunk de nenhuma entrada do acervo real pode ser texto vazio —
    um chunk vazio vira embedding sem sentido e polui a busca."""
    for entry in repository.all_entries():
        for chunk in chunk_entry(entry):
            assert chunk.texto.strip() != "", (
                f"chunk vazio em {chunk.fonte_ref}"
            )
