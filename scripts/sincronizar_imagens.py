#!/usr/bin/env python3
"""Pr?-carrega imagens externas e gera assets WebP/manifesto para o CDN.

Uso:
    python -m scripts.sincronizar_imagens --dry-run --limit 10
    python -m scripts.sincronizar_imagens --fail-on-error

O script n?o altera os JSONs editoriais. Publicar o diret?rio de sa?da em um
bucket/CDN e configurar IMAGE_CDN_BASE_URL ativa as URLs locais na API.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("sincronizar_imagens")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = PROJECT_ROOT / "app" / "data"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "app" / "static" / "img-acervo"
DEFAULT_MANIFEST = DEFAULT_DATA_DIR / "image-manifest.json"
MAX_BYTES = 20 * 1024 * 1024
USER_AGENT = "AcervoCatolicoImageSync/1.0 (contact: suporte@acervocatolico.org)"


@dataclass(frozen=True)
class SyncResult:
    source_url: str
    item: dict[str, Any] | None = None
    error: str | None = None


def collect_image_urls(data_dir: Path) -> list[str]:
    """Coleta URLs HTTP ?nicas dos JSONs do acervo e de suas tradu??es."""
    urls: set[str] = set()
    for path in data_dir.rglob("*.json"):
        if path.name == "image-manifest.json":
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        for entry in payload.get("itens", []):
            image = entry.get("imagem")
            if isinstance(image, str) and urlparse(image).scheme in {"http", "https"}:
                urls.add(image)
    return sorted(urls)


def asset_filename(source_url: str) -> str:
    """Nome imut?vel e determin?stico; trocar a origem cria outro arquivo."""
    return f"{hashlib.sha256(source_url.encode()).hexdigest()}.webp"


def load_manifest(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    images = payload.get("images", {})
    if payload.get("version") != 1 or not isinstance(images, dict):
        raise ValueError(f"{path}: manifesto inv?lido.")
    return images


async def download_image(
    client: httpx.AsyncClient, source_url: str, timeout: float, retries: int
) -> bytes:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            async with client.stream("GET", source_url, timeout=timeout) as response:
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").split(";")[0]
                if not content_type.startswith("image/"):
                    raise ValueError(f"Content-Type n?o ? imagem: {content_type or 'ausente'}")
                chunks: list[bytes] = []
                total = 0
                async for chunk in response.aiter_bytes():
                    total += len(chunk)
                    if total > MAX_BYTES:
                        raise ValueError(f"Imagem ultrapassa o limite de {MAX_BYTES // 1024 // 1024} MB")
                    chunks.append(chunk)
                return b"".join(chunks)
        except (httpx.HTTPError, ValueError) as exc:
            last_error = exc
            if attempt < retries:
                await asyncio.sleep(2**attempt)
    raise RuntimeError(str(last_error))


def convert_to_webp(raw: bytes, max_width: int, quality: int) -> tuple[bytes, int, int]:
    """Converte em mem?ria; Pillow s? ? exigido no job de publica??o."""
    from PIL import Image, UnidentifiedImageError

    try:
        with Image.open(BytesIO(raw)) as image:
            image.load()
            if image.mode not in {"RGB", "RGBA"}:
                image = image.convert("RGBA" if "transparency" in image.info else "RGB")
            image.thumbnail((max_width, max_width * 3))
            output = BytesIO()
            image.save(output, format="WEBP", quality=quality, method=6)
            return output.getvalue(), image.width, image.height
    except (OSError, UnidentifiedImageError) as exc:
        raise ValueError(f"Arquivo n?o p?de ser convertido em WebP: {exc}") from exc


async def sync_one(
    source_url: str,
    client: httpx.AsyncClient,
    output_dir: Path,
    max_width: int,
    quality: int,
    timeout: float,
    retries: int,
    semaphore: asyncio.Semaphore,
) -> SyncResult:
    filename = asset_filename(source_url)
    destination = output_dir / filename
    public_path = f"/img-acervo/{filename}"
    if destination.is_file():
        return SyncResult(source_url, {"path": public_path, "cached": True})

    async with semaphore:
        try:
            raw = await download_image(client, source_url, timeout, retries)
            webp, width, height = convert_to_webp(raw, max_width, quality)
            output_dir.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_suffix(".tmp")
            temporary.write_bytes(webp)
            temporary.replace(destination)
            return SyncResult(
                source_url,
                {"path": public_path, "bytes": len(webp), "width": width, "height": height},
            )
        except Exception as exc:
            return SyncResult(source_url, error=str(exc))


def write_manifest(path: Path, images: dict[str, dict[str, Any]]) -> None:
    payload = {
        "version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "images": images,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


async def run(args: argparse.Namespace) -> int:
    if args.workers < 1 or args.max_width < 1 or not 1 <= args.quality <= 100:
        raise ValueError("workers e largura devem ser positivos; quality deve estar entre 1 e 100.")
    if args.timeout <= 0 or args.retries < 0 or (args.limit is not None and args.limit < 1):
        raise ValueError("timeout deve ser positivo; retries e limit n?o podem ser negativos.")

    all_urls = collect_image_urls(args.data_dir)
    urls = all_urls
    if args.limit is not None:
        urls = urls[: args.limit]
    existing = load_manifest(args.manifest)
    logger.info("%d URLs remotas ?nicas encontradas.", len(urls))

    if args.dry_run:
        logger.info("Dry-run: nenhuma imagem ou manifesto foi gravado.")
        return 0

    semaphore = asyncio.Semaphore(args.workers)
    headers = {"User-Agent": USER_AGENT, "Accept": "image/avif,image/webp,image/*,*/*;q=0.8"}
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        results = await asyncio.gather(
            *(
                sync_one(
                    url, client, args.output_dir, args.max_width, args.quality,
                    args.timeout, args.retries, semaphore,
                )
                for url in urls
            )
        )

    images = {
        url: existing[url]
        for url in all_urls
        if url in existing and (args.output_dir / asset_filename(url)).is_file()
    }
    failures = [result for result in results if result.error]
    for result in results:
        if result.item:
            images[result.source_url] = result.item
    write_manifest(args.manifest, images)

    for failure in failures:
        logger.error("%s: %s", failure.source_url, failure.error)
    logger.info("Sincronizadas: %d; falhas: %d.", len(images), len(failures))
    return 1 if failures and args.fail_on_error else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--max-width", type=int, default=1600)
    parser.add_argument("--quality", type=int, default=82)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--fail-on-error", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(run(parse_args())))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        sys.exit(f"Erro de sincroniza??o: {exc}")
