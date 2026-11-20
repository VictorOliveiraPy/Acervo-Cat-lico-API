"""Reels e pedidos de vídeo: regras puras."""

from __future__ import annotations

import pytest

from app.domain.studio.rules import (
    REEL_THEMES,
    VIDEO_FORMATS,
    ValidationError,
    clean_reel_patch,
    new_reel,
    new_request,
    slugify,
)


def test_slugify_matches_the_studio() -> None:
    assert slugify("São Leão Magno, Papa!") == "sao-leao-magno-papa"
    assert slugify("   ") == "video"
    assert len(slugify("x" * 200)) <= 60


def test_new_reel_validates_everything_the_site_shows() -> None:
    reel = new_reel(
        {
            "slug": "sao-jose",
            "titulo": " São José ",
            "legenda": "Pai.",
            "tema": "santos",
            "largura": 720,
            "altura": 1280,
            "video_url": "https://img.x/reels/sao-jose.mp4",
            "capa_url": "/reels/sao-jose.jpg",
        }
    )
    assert reel.title == "São José" and reel.published is False

    for bad in (
        {"slug": "Com Espaço"},
        {"tema": "inventado"},
        {"titulo": ""},
        {"titulo": "x" * 141},
        {"legenda": "x" * 2201},
        {"video_url": "javascript:alert(1)"},
        {"largura": 0},
    ):
        base = {
            "slug": "a",
            "titulo": "T",
            "legenda": "",
            "tema": "santos",
            "largura": 720,
            "altura": 1280,
            "video_url": "https://a/b.mp4",
            "capa_url": "https://a/b.jpg",
        }
        with pytest.raises(ValidationError):
            new_reel({**base, **bad})


def test_patch_accepts_only_editable_fields() -> None:
    assert clean_reel_patch({"titulo": " Novo ", "publicado": True}) == {
        "title": "Novo",
        "published": True,
    }
    with pytest.raises(ValidationError):
        clean_reel_patch({"slug": "outro"})  # o endereço do vídeo não muda
    with pytest.raises(ValidationError):
        clean_reel_patch({"tema": "inventado"})
    with pytest.raises(ValidationError):
        clean_reel_patch({})


def test_new_request_needs_a_theme_and_a_known_format() -> None:
    req = new_request(
        {
            "tema": " A confissão ",
            "pergunta": "O padre pode contar?",
            "formato": "cinema",
        }
    )
    assert (req.theme, req.question, req.format) == (
        "A confissão",
        "O padre pode contar?",
        "cinema",
    )
    assert new_request({"tema": "Missa"}).format == "cinema"
    with pytest.raises(ValidationError):
        new_request({"tema": ""})
    with pytest.raises(ValidationError):
        new_request({"tema": "x", "formato": "novela"})
    with pytest.raises(ValidationError):
        new_request({"tema": "x", "formato": "meme"})  # o meme saiu do painel
    assert new_request({"tema": "Os sacramentos", "formato": "catequese"}).format == "catequese"
    with pytest.raises(ValidationError):
        new_request({"tema": "x", "pergunta": "Sem interrogação"})


def test_known_lists() -> None:
    assert "santos" in REEL_THEMES and "curiosidades" in REEL_THEMES
    assert VIDEO_FORMATS == ("cinema", "catequese")
