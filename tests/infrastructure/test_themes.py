"""Normalização de tags em temas, e o que o repositório real expõe a partir dela."""

from __future__ import annotations

from collections import Counter

import pytest

from app.core.exceptions import ThemeNotFoundException
from app.infrastructure.acervo.json_repository import Repository
from app.infrastructure.acervo.themes import theme_name, theme_slug


@pytest.fixture(scope="module")
def repo() -> Repository:
    repository = Repository()
    repository.load()
    return repository


@pytest.mark.parametrize(
    ("tag", "slug"),
    [
        ("Espírito Santo", "espirito-santo"),
        ("espírito santo", "espirito-santo"),
        ("Theotókos", "theotokos"),
        ("Pai Nosso", "pai-nosso"),
        ("pai-nosso", "pai-nosso"),
        ("Bispo", "bispos"),
        ("bispos", "bispos"),
        ("Sinai", "sinai"),
        ("???", ""),
    ],
)
def test_should_normalize_tag_to_theme_slug(tag: str, slug: str) -> None:
    assert theme_slug(tag) == slug


def test_should_prefer_most_used_spelling_of_the_slug_itself() -> None:
    assert theme_name(Counter({"bispo": 13, "bispos": 8}), "bispos") == "Bispos"
    assert theme_name(Counter({"pai-nosso": 10, "Pai-Nosso": 3}), "pai-nosso") == "Pai-nosso"


def test_should_list_themes_filtered_by_minimum_total(repo: Repository) -> None:
    themes = repo.list_themes(min_total=3)
    slugs = [theme.slug for theme in themes]
    assert "franciscanos" in slugs
    assert slugs == sorted(slugs)
    assert all(theme.total >= 3 for theme in themes)


def test_should_page_theme_entries_grouped_by_category(repo: Repository) -> None:
    page = repo.get_theme("franciscanos", limit=5, offset=0)
    assert page.nome == "Franciscanos"
    assert page.total >= 5
    assert len(page.itens) == 5

    everything = repo.get_theme("franciscanos", limit=page.total, offset=0).itens
    categories = [entry.categoria for entry in everything]
    assert len({(e.categoria, e.slug) for e in everything}) == page.total
    # Categoria não reaparece depois de encerrada: a lista já vem agrupada.
    assert categories == sorted(categories, key=list(dict.fromkeys(categories)).index)


def test_should_not_count_an_entry_twice_when_two_tags_share_a_slug(repo: Repository) -> None:
    for theme in repo.list_themes():
        keys = [
            (entry.categoria, entry.slug)
            for entry in repo.get_theme(theme.slug, limit=theme.total, offset=0).itens
        ]
        assert len(keys) == len(set(keys))


def test_should_expose_entry_themes_that_resolve(repo: Repository) -> None:
    entry = repo.get_by_slug("santos", "francisco-de-assis")
    assert len(entry.temas) > 0
    for theme in entry.temas:
        assert repo.get_theme(theme.slug, limit=1, offset=0).total >= 1


def test_should_raise_for_unknown_theme(repo: Repository) -> None:
    with pytest.raises(ThemeNotFoundException):
        repo.get_theme("nao-existe", limit=1, offset=0)
