# -*- coding: utf-8 -*-
"""Gerador de carrossel narrativo ('história') — mesma identidade visual dos
posts (bordô + dourado + Playfair/EB Garamond), com uma pintura de domínio
público na capa e paginação em pontinhos.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from identidade import (
    BG_DEEP,
    BG_MID,
    CREAM,
    GOLD,
    GOLD_SOFT,
    SCALE,
    _radial_bg,
    _wrap,
    draw_logo_mark,
    font,
)

ARTE_DIR = Path(__file__).resolve().parent / "arte"
W, H = 1080 * SCALE, 1350 * SCALE


def _dots(d: ImageDraw.ImageDraw, index: int, total: int) -> None:
    r = 7 * SCALE
    gap = 22 * SCALE
    total_w = total * gap
    x0 = (W - total_w) / 2 + gap / 2
    y = H - 46 * SCALE
    for i in range(total):
        x = x0 + i * gap
        color = GOLD if i == index else (GOLD_SOFT if False else (110, 60, 70))
        d.ellipse([x - r, y - r, x + r, y + r], fill=color if i != index else GOLD)


def make_cover_slide(
    art_key: str,
    eyebrow: str,
    title: str,
    swipe_hint: str,
    out_path: Path,
    index: int,
    total: int,
) -> None:
    img = Image.open(ARTE_DIR / f"{art_key}.jpg").convert("RGB")
    target_ratio = W / H
    w, h = img.size
    cur_ratio = w / h
    if cur_ratio > target_ratio:
        new_w = int(h * target_ratio)
        x0 = (w - new_w) // 2
        img = img.crop((x0, 0, x0 + new_w, h))
    else:
        new_h = int(w / target_ratio)
        y0 = int((h - new_h) * 0.25)
        img = img.crop((0, y0, w, y0 + new_h))
    img = img.resize((W, H), Image.LANCZOS)

    overlay = Image.new("L", (W, H), 0)
    od = ImageDraw.Draw(overlay)
    band_h = int(H * 0.55)
    for i in range(band_h):
        alpha = int(235 * (i / band_h) ** 1.5)
        od.line([(0, H - band_h + i), (W, H - band_h + i)], fill=alpha)
    od.rectangle([0, 0, W, int(H * 0.14)], fill=140)
    dark = Image.new("RGB", (W, H), (14, 8, 10))
    img = Image.composite(dark, img, overlay)

    d = ImageDraw.Draw(img)
    f_eyebrow = font("EBGaramond.ttf", 22, 600)
    f_title = font("PlayfairDisplay.ttf", 66, 800)
    f_hint = font("EBGaramond.ttf", 24, 500)

    spaced = " ".join(list(eyebrow.upper()))
    tw = d.textlength(spaced, font=f_eyebrow)
    d.text(((W - tw) / 2, 60 * SCALE), spaced, font=f_eyebrow, fill=GOLD_SOFT)

    lines = _wrap(d, title, f_title, W - 180 * SCALE)
    y = H - 260 * SCALE - (len(lines) - 1) * 78 * SCALE
    for line in lines:
        tw = d.textlength(line, font=f_title)
        d.text(((W - tw) / 2, y), line, font=f_title, fill=GOLD)
        y += 78 * SCALE

    tw = d.textlength(swipe_hint, font=f_hint)
    d.text(((W - tw) / 2, H - 130 * SCALE), swipe_hint, font=f_hint, fill=CREAM)

    _dots(d, index, total)
    _corner_logo(d)

    final = img.resize((1080, 1350), Image.LANCZOS)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    final.save(out_path, quality=92)


def _corner_logo(d: ImageDraw.ImageDraw) -> None:
    """Selo discreto no canto superior direito — presente em todo slide do
    carrossel, não só na capa/CTA, pra marca aparecer mesmo se alguém parar
    de arrastar no meio da história."""
    cx, cy, r = W - 90 * SCALE, 90 * SCALE, 22
    backing_r = r * SCALE * 1.3
    d.ellipse([cx - backing_r, cy - backing_r, cx + backing_r, cy + backing_r], fill=(14, 8, 10))
    draw_logo_mark(d, cx, cy, r=r)


def make_text_slide(
    label: str,
    body: str,
    out_path: Path,
    index: int,
    total: int,
    background_art: str | None = None,
    background_crop: tuple[float, float, float, float] | None = None,
) -> None:
    if background_art:
        img = Image.open(ARTE_DIR / f"{background_art}.jpg").convert("RGB")
        if background_crop:
            w, h = img.size
            l, t, r, b = background_crop
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
            y0 = int((h - new_h) * 0.2)
            img = img.crop((0, y0, w, y0 + new_h))
        img = img.resize((W, H), Image.LANCZOS)
        dark = Image.new("RGB", (W, H), (16, 9, 11))
        img = Image.blend(img, dark, 0.62)
    else:
        img = _radial_bg()

    d = ImageDraw.Draw(img)
    margin = 58 * SCALE
    d.rectangle([margin, margin, W - margin, H - margin], outline=GOLD_SOFT, width=2 * SCALE)

    f_label = font("EBGaramond.ttf", 22, 600)
    f_body = font("PlayfairDisplay.ttf", 40, 600)

    spaced = " ".join(list(label.upper()))
    tw = d.textlength(spaced, font=f_label)
    d.text(((W - tw) / 2, 150 * SCALE), spaced, font=f_label, fill=GOLD_SOFT)

    line_w = 90 * SCALE
    y_line = 210 * SCALE
    d.line([(W - line_w) / 2, y_line, (W + line_w) / 2, y_line], fill=GOLD_SOFT, width=2 * SCALE)

    lines = _wrap(d, body, f_body, W - 260 * SCALE)
    line_h = 62 * SCALE
    total_h = line_h * len(lines)
    y = (H - total_h) / 2
    for line in lines:
        tw = d.textlength(line, font=f_body)
        d.text(((W - tw) / 2, y), line, font=f_body, fill=CREAM)
        y += line_h

    _dots(d, index, total)
    _corner_logo(d)

    final = img.resize((1080, 1350), Image.LANCZOS)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    final.save(out_path, quality=92)


def make_cta_slide(closing: str, url: str, out_path: Path, index: int, total: int) -> None:
    img = _radial_bg()
    d = ImageDraw.Draw(img)
    margin = 58 * SCALE
    d.rectangle([margin, margin, W - margin, H - margin], outline=GOLD_SOFT, width=2 * SCALE)

    f_body = font("EBGaramond.ttf", 34, 500)
    f_url = font("PlayfairDisplay.ttf", 40, 700)

    lines = _wrap(d, closing, f_body, W - 300 * SCALE)
    line_h = 52 * SCALE
    total_h = line_h * len(lines)
    y = H * 0.42 - total_h / 2
    for line in lines:
        tw = d.textlength(line, font=f_body)
        d.text(((W - tw) / 2, y), line, font=f_body, fill=CREAM)
        y += line_h

    y += 40 * SCALE
    line_w = 90 * SCALE
    d.line([(W - line_w) / 2, y, (W + line_w) / 2, y], fill=GOLD_SOFT, width=2 * SCALE)
    y += 54 * SCALE

    tw = d.textlength(url, font=f_url)
    d.text(((W - tw) / 2, y), url, font=f_url, fill=GOLD)
    y += 60 * SCALE

    draw_logo_mark(d, W / 2, y + 26 * SCALE, r=26)
    _dots(d, index, total)

    final = img.resize((1080, 1350), Image.LANCZOS)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    final.save(out_path, quality=92)
