# -*- coding: utf-8 -*-
"""Gerador de memes: arte sacra de dominio publico + legenda bold, no mesmo
formato popular de meme (texto com contorno, sobre a imagem) + marca discreta
do Compendio Catolico no canto.

Renderiza em 2x (mesma convencao de identidade.py) e reduz no final, pra
texto e contorno ficarem com antialiasing suave.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from identidade import GOLD, SCALE, draw_logo_mark, font  # reaproveita fontes/escala/marca já usadas nos posts

ARTE_DIR = Path(__file__).resolve().parent / "arte"

W, H = 1080 * SCALE, 1350 * SCALE


def _wrap(d: ImageDraw.ImageDraw, text: str, f: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        trial = (cur + " " + w).strip()
        if d.textlength(trial, font=f) <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _outlined_text(d: ImageDraw.ImageDraw, xy, text, font_, fill, outline, outline_w) -> None:
    x, y = xy
    for dx in range(-outline_w, outline_w + 1):
        for dy in range(-outline_w, outline_w + 1):
            if dx * dx + dy * dy <= outline_w * outline_w:
                d.text((x + dx, y + dy), text, font=font_, fill=outline)
    d.text((x, y), text, font=font_, fill=fill)


def make_meme(
    art_key: str,
    caption: str,
    out_path: Path,
    position: str = "bottom",
    crop_box: tuple[float, float, float, float] | None = None,
) -> None:
    """position: 'top' ou 'bottom' — onde a legenda entra."""
    img = Image.open(ARTE_DIR / f"{art_key}.jpg").convert("RGB")

    if crop_box:
        w, h = img.size
        l, t, r, b = crop_box
        img = img.crop((int(w * l), int(h * t), int(w * r), int(h * b)))

    target_ratio = W / H
    w, h = img.size
    cur_ratio = w / h
    if cur_ratio > target_ratio:
        new_w = int(h * target_ratio)
        x0 = (w - new_w) // 2
        img = img.crop((x0, 0, x0 + new_w, h))
    else:
        new_h = int(w / target_ratio)
        y0 = int((h - new_h) * 0.35)
        img = img.crop((0, y0, w, y0 + new_h))
    img = img.resize((W, H), Image.LANCZOS)

    overlay = Image.new("L", (W, H), 0)
    od = ImageDraw.Draw(overlay)
    band_h = int(H * 0.32)
    for i in range(band_h):
        alpha = int(190 * (i / band_h) ** 1.3)
        y = H - band_h + i if position != "top" else band_h - i
        od.line([(0, y), (W, y)], fill=alpha)
    dark = Image.new("RGB", (W, H), (10, 6, 8))
    img = Image.composite(dark, img, overlay)

    d = ImageDraw.Draw(img)
    f_caption = font("PlayfairDisplay.ttf", 46, 800)
    max_w = W - 110 * SCALE

    lines = _wrap(d, caption, f_caption, max_w)
    line_h = 58 * SCALE
    total_h = line_h * len(lines)

    y = 56 * SCALE if position == "top" else H - 56 * SCALE - total_h

    for line in lines:
        tw = d.textlength(line, font=f_caption)
        _outlined_text(d, ((W - tw) / 2, y), line, f_caption, (255, 255, 255), (10, 6, 8), 6 * SCALE)
        y += line_h

    logo_r = 24
    logo_cy = H - 56 * SCALE if position == "top" else 56 * SCALE
    backing_r = logo_r * SCALE * 1.25
    d.ellipse(
        [W / 2 - backing_r, logo_cy - backing_r, W / 2 + backing_r, logo_cy + backing_r],
        fill=(10, 6, 8, 255),
    )
    draw_logo_mark(d, W / 2, logo_cy, r=logo_r)

    final = img.resize((1080, 1350), Image.LANCZOS)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    final.save(out_path, quality=92)
