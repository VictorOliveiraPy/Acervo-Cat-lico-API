"""Testes do contrato entre manifesto de imagens e API."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.exceptions import DataIntegrityError
from app.image_assets import ImageAssetResolver
from scripts.sincronizar_imagens import asset_filename, collect_image_urls


def test_should_keep_original_url_when_cdn_is_disabled() -> None:
    source = "https://upload.wikimedia.org/example.jpg"

    assert ImageAssetResolver(None, None).resolve(source) == source


def test_should_resolve_known_image_to_cdn(tmp_path: Path) -> None:
    source = "https://upload.wikimedia.org/example.jpg"
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"version": 1, "images": {source: {"path": "/img-acervo/x.webp"}}}),
        encoding="utf-8",
    )

    resolver = ImageAssetResolver(manifest, "https://cdn.example.com/")

    assert resolver.resolve(source) == "https://cdn.example.com/img-acervo/x.webp"
    assert resolver.resolve("https://upload.wikimedia.org/unknown.jpg") == "https://upload.wikimedia.org/unknown.jpg"


def test_should_reject_missing_manifest_when_cdn_is_enabled(tmp_path: Path) -> None:
    with pytest.raises(DataIntegrityError, match="IMAGE_CDN_BASE_URL"):
        ImageAssetResolver(tmp_path / "missing.json", "https://cdn.example.com")


def test_should_collect_only_remote_images_and_use_deterministic_filename(tmp_path: Path) -> None:
    (tmp_path / "conteudo.json").write_text(
        json.dumps(
            {"itens": [
                {"imagem": "https://upload.wikimedia.org/a.jpg"},
                {"imagem": "https://upload.wikimedia.org/a.jpg"},
                {"imagem": "/img-acervo/local.jpg"},
            ]}
        ),
        encoding="utf-8",
    )

    assert collect_image_urls(tmp_path) == ["https://upload.wikimedia.org/a.jpg"]
    assert asset_filename("https://upload.wikimedia.org/a.jpg") == asset_filename("https://upload.wikimedia.org/a.jpg")
    assert asset_filename("https://upload.wikimedia.org/a.jpg") != asset_filename("https://upload.wikimedia.org/b.jpg")
