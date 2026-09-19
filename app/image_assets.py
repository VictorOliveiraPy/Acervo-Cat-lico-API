"""Leitura do manifesto de imagens pr?-carregadas e resolu??o de URLs CDN."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.exceptions import DataIntegrityError


class ImageAssetResolver:
    """Resolve uma URL editorial para a c?pia publicada no CDN, quando ativa."""

    def __init__(self, manifest_path: Path | None, cdn_base_url: str | None) -> None:
        self._cdn_base_url = cdn_base_url.rstrip("/") if cdn_base_url else None
        self._paths = self._load_manifest(manifest_path) if self._cdn_base_url else {}

    def resolve(self, source_url: str | None) -> str | None:
        """Devolve a URL CDN conhecida ou mant?m a origem durante o rollout."""
        if not source_url or not self._cdn_base_url:
            return source_url
        public_path = self._paths.get(source_url)
        return f"{self._cdn_base_url}{public_path}" if public_path else source_url

    @staticmethod
    def _load_manifest(manifest_path: Path | None) -> dict[str, str]:
        if manifest_path is None or not manifest_path.is_file():
            raise DataIntegrityError(
                "IMAGE_CDN_BASE_URL exige um IMAGE_MANIFEST_PATH existente."
            )
        try:
            payload: Any = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise DataIntegrityError(f"Manifesto de imagens inv?lido: {exc}") from exc

        images = payload.get("images") if isinstance(payload, dict) else None
        if (
            not isinstance(payload, dict)
            or payload.get("version") != 1
            or not isinstance(images, dict)
        ):
            raise DataIntegrityError("Manifesto de imagens n?o segue a vers?o 1.")

        paths: dict[str, str] = {}
        for source_url, item in images.items():
            path = item.get("path") if isinstance(item, dict) else None
            if not isinstance(source_url, str) or not _is_valid_public_path(path):
                raise DataIntegrityError(
                    "Manifesto de imagens cont?m URL ou caminho inv?lido."
                )
            paths[source_url] = path
        return paths


def _is_valid_public_path(path: object) -> bool:
    return (
        isinstance(path, str)
        and path.startswith("/img-acervo/")
        and ".." not in path
        and "?" not in path
        and "#" not in path
    )
