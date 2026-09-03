"""Testes unitários do repositório em memória (sem I/O de rede, sem TestClient)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.exceptions import CategoryNotFoundException, EntryNotFoundException
from app.models import Category
from app.repository import Repository, build_excerpt, normalize


@pytest.fixture(scope="module")
def repository() -> Repository:
    """Repositório carregado com os dados reais de app/data."""
    repo = Repository()
    repo.load()
    return repo


def test_should_load_all_eight_categories_when_starting_up(
    repository: Repository,
) -> None:
    """Toda categoria do enum precisa ter arquivo de dados válido."""
    # Given / When
    categories = repository.list_categories()

    # Then
    assert len(categories) == len(Category)
    assert {info.categoria for info in categories} == set(Category)
    assert all(info.total > 0 for info in categories)


def test_should_expose_editorial_warning_when_listing_categories(
    repository: Repository,
) -> None:
    """O aviso de 'exemplos iniciais' é parte do contrato, não só comentário."""
    # Given / When
    categories = repository.list_categories()

    # Then
    assert all(info.aviso.strip() for info in categories)


def test_should_return_entry_with_specific_fields_when_getting_by_slug(
    repository: Repository,
) -> None:
    """Subclasse precisa serializar seus campos próprios, não só os da base."""
    # Given / When
    santo = repository.get_by_slug(Category.SANTOS, "francisco-de-assis")

    # Then
    assert santo.titulo.startswith("São Francisco")
    assert santo.festa == "4 de outubro"
    assert santo.fontes, "toda entrada precisa de ao menos uma fonte verificável"


def test_should_raise_entry_not_found_when_slug_does_not_exist(
    repository: Repository,
) -> None:
    """Slug inexistente vira exceção de domínio 404, não KeyError."""
    # Given / When / Then
    with pytest.raises(EntryNotFoundException) as excinfo:
        repository.get_by_slug(Category.SANTOS, "santo-inexistente")

    assert excinfo.value.status_code == 404
    assert excinfo.value.code == "ENTRY_NOT_FOUND"


def test_should_raise_category_not_found_when_category_is_unknown(
    repository: Repository,
) -> None:
    """Categoria fora do enum é 404 (URL inexistente), não erro de validação."""
    # Given / When / Then
    with pytest.raises(CategoryNotFoundException):
        repository.list_entries("anjos-da-guarda")


def test_should_paginate_entries_when_limit_and_offset_are_given(
    repository: Repository,
) -> None:
    """Total é o do acervo inteiro; itens respeitam a janela pedida."""
    # Given
    full = repository.list_entries(Category.CATECISMO, limit=50, offset=0)

    # When
    page = repository.list_entries(Category.CATECISMO, limit=2, offset=1)

    # Then
    assert page.total == full.total
    assert len(page.itens) == 2
    assert page.itens[0].slug == full.itens[1].slug


def test_should_sort_by_explicit_order_when_category_defines_it(
    repository: Repository,
) -> None:
    """As partes do Catecismo saem na ordem canônica, não em ordem alfabética."""
    # Given / When
    page = repository.list_entries(Category.CATECISMO, limit=50)

    # Then
    ordens = [item.ordem for item in page.itens]
    assert ordens == sorted(o for o in ordens if o is not None)
    assert page.itens[0].ordem == 1


def test_should_find_entry_when_query_ignores_case_and_accents(
    repository: Repository,
) -> None:
    """'assisi' sem acento/caixa precisa achar 'Assis' no corpo do texto."""
    # Given / When
    results = repository.search("ASSIS")

    # Then
    slugs = {result.slug for result in results}
    assert "francisco-de-assis" in slugs
    assert all(result.trecho.strip() for result in results)


def test_should_restrict_results_when_category_filter_is_given(
    repository: Repository,
) -> None:
    """Filtro de categoria não deve vazar resultado de outra categoria."""
    # Given / When
    results = repository.search("Teresa", categoria=Category.DOUTORES_IGREJA)

    # Then
    assert results
    assert all(result.categoria == Category.DOUTORES_IGREJA for result in results)


def test_should_respect_limit_when_search_matches_many_entries(
    repository: Repository,
) -> None:
    """Limite é teto rígido do resultado da busca."""
    # Given / When
    results = repository.search("igreja", limit=3)

    # Then
    assert len(results) <= 3


def test_should_return_empty_list_when_query_matches_nothing(
    repository: Repository,
) -> None:
    """Busca sem resultado devolve lista vazia, não erro."""
    # Given / When
    results = repository.search("xyzzyplugh")

    # Then
    assert results == []


def test_should_match_tag_when_query_is_only_in_tags(
    repository: Repository,
) -> None:
    """Tags também são indexadas; o trecho cai no resumo, que tem contexto."""
    # Given / When
    results = repository.search("capuchinhos")

    # Then
    assert any(result.slug == "pio-de-pietrelcina" for result in results)


def test_should_keep_term_inside_excerpt_when_match_is_in_the_middle() -> None:
    """O trecho precisa conter o termo com contexto ao redor, não o texto todo."""
    # Given
    text = "palavra " * 40 + "eucaristia " + "palavra " * 40
    normalized = normalize(text)

    # When
    excerpt = build_excerpt(text, normalized, normalized.index("eucaristia"), 10)

    # Then
    assert "eucaristia" in excerpt
    assert len(excerpt) < len(text)
    assert excerpt.startswith("…") and excerpt.endswith("…")


def test_should_fail_loading_when_json_has_unknown_field(tmp_path: Path) -> None:
    """Campo desconhecido no JSON derruba a carga em vez de ser ignorado."""
    # Given
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    broken = {
        "_meta": {
            "categoria": "santos",
            "nome": "Santos",
            "descricao": "x",
            "status": "exemplos-iniciais",
            "aviso": "x",
        },
        "itens": [
            {
                "id": "santos:teste",
                "slug": "teste",
                "titulo": "Teste",
                "resumo": "x",
                "corpo": "x",
                "categoria": "santos",
                "festas": "campo com typo",
            }
        ],
    }
    (data_dir / "santos.json").write_text(json.dumps(broken), encoding="utf-8")

    # When / Then
    with pytest.raises(ValueError, match="santos.json"):
        Repository(data_dir=data_dir).load()
