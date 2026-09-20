# -*- coding: utf-8 -*-
"""Gerador de cards de cena (Reels) e slide (Stories) — mesma identidade
visual bordô/dourada, um card por cena/beat, pra nunca sobrar formato "só
texto" sem nenhuma imagem pronta pra postar/editar.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from identidade import CREAM, GOLD, GOLD_SOFT, SCALE, _radial_bg, _wrap, draw_logo_mark, font

W, H = 1080 * SCALE, 1350 * SCALE


def make_scene_card(
    timecode: str,
    headline: str,
    visual_note: str,
    out_path: Path,
    accent: str = "reel",
) -> None:
    """Card de uma cena de Reel: código de tempo + frase grande da tela +
    nota pequena de qual imagem/ação usar naquele momento."""
    img = _radial_bg()
    d = ImageDraw.Draw(img)
    margin = 58 * SCALE
    d.rectangle([margin, margin, W - margin, H - margin], outline=GOLD_SOFT, width=2 * SCALE)

    f_time = font("EBGaramond.ttf", 24, 600)
    f_head = font("PlayfairDisplay.ttf", 54, 800)
    f_note = font("EBGaramond.ttf", 26, 450)

    label = f"CENA · {timecode}" if accent == "reel" else timecode
    spaced = " ".join(list(label.upper()))
    tw = d.textlength(spaced, font=f_time)
    d.text(((W - tw) / 2, 130 * SCALE), spaced, font=f_time, fill=GOLD_SOFT)

    line_w = 90 * SCALE
    y_line = 186 * SCALE
    d.line([(W - line_w) / 2, y_line, (W + line_w) / 2, y_line], fill=GOLD_SOFT, width=2 * SCALE)

    lines = _wrap(d, headline, f_head, W - 220 * SCALE)
    line_h = 70 * SCALE
    total_h = line_h * len(lines)
    y = H * 0.44 - total_h / 2
    for line in lines:
        tw = d.textlength(line, font=f_head)
        d.text(((W - tw) / 2, y), line, font=f_head, fill=GOLD)
        y += line_h

    y = H * 0.72
    note_lines = _wrap(d, visual_note, f_note, W - 300 * SCALE)
    for line in note_lines[:4]:
        tw = d.textlength(line, font=f_note)
        d.text(((W - tw) / 2, y), line, font=f_note, fill=CREAM)
        y += 40 * SCALE

    draw_logo_mark(d, W / 2, H - 90 * SCALE, r=26)

    final = img.resize((1080, 1350), Image.LANCZOS)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    final.save(out_path, quality=92)


def make_story_slide_card(
    kicker: str,
    text: str,
    sticker_note: str,
    out_path: Path,
) -> None:
    """Card de um slide de Story: pergunta/frase grande + nota de qual
    sticker nativo do Instagram colar em cima depois de publicar."""
    img = _radial_bg()
    d = ImageDraw.Draw(img)
    margin = 58 * SCALE
    d.rectangle([margin, margin, W - margin, H - margin], outline=GOLD_SOFT, width=2 * SCALE)

    f_kicker = font("EBGaramond.ttf", 24, 600)
    f_text = font("PlayfairDisplay.ttf", 52, 700)
    f_note = font("EBGaramond.ttf", 24, 500)

    spaced = " ".join(list(kicker.upper()))
    tw = d.textlength(spaced, font=f_kicker)
    d.text(((W - tw) / 2, 140 * SCALE), spaced, font=f_kicker, fill=GOLD_SOFT)

    line_w = 90 * SCALE
    y_line = 196 * SCALE
    d.line([(W - line_w) / 2, y_line, (W + line_w) / 2, y_line], fill=GOLD_SOFT, width=2 * SCALE)

    lines = _wrap(d, text, f_text, W - 220 * SCALE)
    line_h = 68 * SCALE
    total_h = line_h * len(lines)
    y = H * 0.46 - total_h / 2
    for line in lines:
        tw = d.textlength(line, font=f_text)
        d.text(((W - tw) / 2, y), line, font=f_text, fill=CREAM)
        y += line_h

    if sticker_note:
        box_w = W - 200 * SCALE
        box_h = 130 * SCALE
        box_x0 = (W - box_w) / 2
        box_y0 = H * 0.76
        d.rounded_rectangle(
            [box_x0, box_y0, box_x0 + box_w, box_y0 + box_h],
            radius=16 * SCALE,
            outline=GOLD,
            width=3 * SCALE,
        )
        note_lines = _wrap(d, sticker_note, f_note, box_w - 60 * SCALE)
        ny = box_y0 + (box_h - len(note_lines) * 34 * SCALE) / 2
        for line in note_lines:
            tw = d.textlength(line, font=f_note)
            d.text(((W - tw) / 2, ny), line, font=f_note, fill=GOLD)
            ny += 34 * SCALE

    draw_logo_mark(d, W / 2, H - 90 * SCALE, r=24)

    final = img.resize((1080, 1350), Image.LANCZOS)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    final.save(out_path, quality=92)
