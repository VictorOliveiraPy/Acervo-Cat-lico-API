"""Motor de geração dos posts estáticos do Instagram — replica a identidade
visual já usada em post-velas.png (bordô + dourado, moldura fina, serifada).

Fontes: Playfair Display (títulos) + EB Garamond (corpo/eyebrow), baixadas do
repositório oficial google/fonts (licença OFL, incluída em fonts/) — sem
dependência de rede pra rodar de novo depois.
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONTS_DIR = Path(__file__).resolve().parent / "fonts"
ARTE_DIR = Path(__file__).resolve().parent / "arte"

SCALE = 2
W, H = 1080 * SCALE, 1350 * SCALE

BG_DEEP = (46, 10, 20)
BG_MID = (92, 20, 34)
GOLD = (222, 189, 128)
GOLD_SOFT = (196, 158, 94)
CREAM = (232, 220, 205)

_FONT_CACHE: dict[tuple[str, int, int | None], ImageFont.FreeTypeFont] = {}


def font(name: str, size: int, weight: int | None = None) -> ImageFont.FreeTypeFont:
    key = (name, size, weight)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    f = ImageFont.truetype(str(FONTS_DIR / name), size * SCALE)
    if weight is not None:
        try:
            f.set_variation_by_axes([weight])
        except Exception:
            pass
    _FONT_CACHE[key] = f
    return f


def _radial_bg() -> Image.Image:
    img = Image.new("RGB", (W, H), BG_DEEP)
    overlay = Image.new("L", (W, H), 0)
    od = ImageDraw.Draw(overlay)
    cx, cy = W // 2, int(H * 0.30)
    max_r = int(W * 0.95)
    for r in range(max_r, 0, -4):
        alpha = int(255 * (1 - r / max_r) ** 1.6)
        od.ellipse([cx - r, cy - r, cx + r, cy + r], fill=alpha)
    glow = Image.new("RGB", (W, H), BG_MID)
    return Image.composite(glow, img, overlay)


def _draw_frame(d: ImageDraw.ImageDraw) -> None:
    margin = 58 * SCALE
    d.rectangle([margin, margin, W - margin, H - margin], outline=GOLD_SOFT, width=2 * SCALE)


def _photo_top_bg(art_key: str, crop_box: tuple[float, float, float, float] | None = None) -> Image.Image:
    """Fundo com uma foto/pintura real preenchendo o topo do post, esmaecendo
    pro bordô da marca a partir de onde o texto começa (~42% da altura) —
    pra todo post ter uma imagem de verdade, não só o ícone abstrato."""
    photo = Image.open(ARTE_DIR / f"{art_key}.jpg").convert("RGB")
    if crop_box:
        w, h = photo.size
        l, t, r, b = crop_box
        photo = photo.crop((int(w * l), int(h * t), int(w * r), int(h * b)))

    target_ratio = W / H
    w, h = photo.size
    cur_ratio = w / h
    if cur_ratio > target_ratio:
        new_w = int(h * target_ratio)
        x0 = (w - new_w) // 2
        photo = photo.crop((x0, 0, x0 + new_w, h))
    else:
        new_h = int(w / target_ratio)
        y0 = int((h - new_h) * 0.25)
        photo = photo.crop((0, y0, w, y0 + new_h))
    photo = photo.resize((W, H), Image.LANCZOS)

    fade_start = int(H * 0.24)
    fade_end = int(H * 0.43)
    mask = Image.new("L", (W, H), 255)
    md = ImageDraw.Draw(mask)
    md.rectangle([0, fade_end, W, H], fill=0)
    for y in range(fade_start, fade_end):
        alpha = int(255 * (1 - (y - fade_start) / (fade_end - fade_start)))
        md.line([(0, y), (W, y)], fill=alpha)

    base = _radial_bg()
    return Image.composite(photo, base, mask)


def draw_logo_mark(d: ImageDraw.ImageDraw, cx: float, cy: float, r: float = 46) -> None:
    """O selo da marca: anel duplo dourado com um "C" serifado no centro —
    mesmo logo já usado nos posts de citação do Compêndio Católico. Chamado
    em todo gerador (posts, memes, histórias, reels, stories) pra manter a
    marca consistente em qualquer imagem publicada."""
    r = r * SCALE
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=GOLD, width=max(2, int(r * 0.12)))
    r2 = r * 0.86
    d.ellipse([cx - r2, cy - r2, cx + r2, cy + r2], outline=GOLD_SOFT, width=max(1, int(r * 0.035)))
    f_c = font("PlayfairDisplay.ttf", int(r / SCALE * 1.15), 800)
    tw = d.textlength("C", font=f_c)
    bbox = d.textbbox((0, 0), "C", font=f_c)
    th = bbox[3] - bbox[1]
    d.text((cx - tw / 2, cy - th / 2 - bbox[1]), "C", font=f_c, fill=CREAM)


def _rays(d: ImageDraw.ImageDraw, cx: float, cy: float, r0: float, r1: float, count: int, width: int, color) -> None:
    for i in range(count):
        ang = math.radians(360 / count * i - 90)
        sx, sy = cx + math.cos(ang) * r0, cy + math.sin(ang) * r0
        ex, ey = cx + math.cos(ang) * r1, cy + math.sin(ang) * r1
        d.line([sx, sy, ex, ey], fill=color, width=width)


def _icon_candle(d: ImageDraw.ImageDraw, cx: int, top: int) -> None:
    body_w, body_h = 74 * SCALE, 130 * SCALE
    x0, y0 = cx - body_w // 2, top + 90 * SCALE
    x1, y1 = cx + body_w // 2, y0 + body_h
    d.rounded_rectangle([x0, y0, x1, y1], radius=10 * SCALE, fill=GOLD)
    d.line([x0 + 8 * SCALE, y0 + 22 * SCALE, x1 - 8 * SCALE, y0 + 22 * SCALE], fill=BG_DEEP, width=3 * SCALE)
    fx, fy = cx, y0 - 48 * SCALE
    d.polygon(
        [(fx, fy - 34 * SCALE), (fx + 16 * SCALE, fy + 6 * SCALE), (fx, fy + 20 * SCALE), (fx - 16 * SCALE, fy + 6 * SCALE)],
        fill=GOLD,
    )
    _rays(d, fx, fy - 6 * SCALE, 34 * SCALE, 58 * SCALE, 5, 3 * SCALE, GOLD_SOFT)


def _icon_chalice(d: ImageDraw.ImageDraw, cx: int, top: int) -> None:
    y = top + 70 * SCALE
    bowl_w = 96 * SCALE
    d.pieslice([cx - bowl_w // 2, y, cx + bowl_w // 2, y + bowl_w], 0, 180, fill=GOLD)
    d.rectangle([cx - 10 * SCALE, y + bowl_w // 2 - 4 * SCALE, cx + 10 * SCALE, y + bowl_w // 2 + 70 * SCALE], fill=GOLD)
    base_w = 84 * SCALE
    base_y = y + bowl_w // 2 + 70 * SCALE
    d.rounded_rectangle([cx - base_w // 2, base_y, cx + base_w // 2, base_y + 16 * SCALE], radius=8 * SCALE, fill=GOLD)
    _rays(d, cx, y - 10 * SCALE, 20 * SCALE, 52 * SCALE, 5, 3 * SCALE, GOLD_SOFT)


def _icon_halo(d: ImageDraw.ImageDraw, cx: int, top: int) -> None:
    cy = top + 120 * SCALE
    r = 52 * SCALE
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=GOLD, width=6 * SCALE)
    _rays(d, cx, cy, r + 14 * SCALE, r + 44 * SCALE, 12, 3 * SCALE, GOLD_SOFT)


def _icon_cross(d: ImageDraw.ImageDraw, cx: int, top: int) -> None:
    y0 = top + 60 * SCALE
    v_w, v_h = 22 * SCALE, 150 * SCALE
    h_w, h_h = 96 * SCALE, 22 * SCALE
    d.rounded_rectangle([cx - v_w // 2, y0, cx + v_w // 2, y0 + v_h], radius=8 * SCALE, fill=GOLD)
    hy = y0 + 34 * SCALE
    d.rounded_rectangle([cx - h_w // 2, hy, cx + h_w // 2, hy + h_h], radius=8 * SCALE, fill=GOLD)
    _rays(d, cx, y0 - 6 * SCALE, 14 * SCALE, 40 * SCALE, 5, 3 * SCALE, GOLD_SOFT)


def _icon_book(d: ImageDraw.ImageDraw, cx: int, top: int) -> None:
    y0 = top + 90 * SCALE
    half_w = 96 * SCALE
    h = 76 * SCALE
    d.polygon([(cx, y0 + 14 * SCALE), (cx - half_w, y0), (cx - half_w, y0 + h), (cx, y0 + h + 14 * SCALE)], fill=GOLD)
    d.polygon([(cx, y0 + 14 * SCALE), (cx + half_w, y0), (cx + half_w, y0 + h), (cx, y0 + h + 14 * SCALE)], fill=GOLD)
    d.line([cx, y0 + 14 * SCALE, cx, y0 + h + 14 * SCALE], fill=BG_DEEP, width=3 * SCALE)
    for i in range(3):
        yy = y0 + 20 * SCALE + i * 16 * SCALE
        d.line([cx - half_w + 16 * SCALE, yy, cx - 14 * SCALE, yy], fill=BG_DEEP, width=2 * SCALE)
        d.line([cx + 14 * SCALE, yy, cx + half_w - 16 * SCALE, yy], fill=BG_DEEP, width=2 * SCALE)
    _rays(d, cx, y0 - 20 * SCALE, 14 * SCALE, 38 * SCALE, 5, 3 * SCALE, GOLD_SOFT)


def _icon_lamp(d: ImageDraw.ImageDraw, cx: int, top: int) -> None:
    y0 = top + 110 * SCALE
    body_w = 90 * SCALE
    d.ellipse([cx - body_w // 2, y0, cx + body_w // 2, y0 + body_w * 0.7], fill=GOLD)
    d.polygon([(cx + body_w * 0.3, y0 + body_w * 0.35), (cx + body_w * 0.75, y0 + body_w * 0.2), (cx + body_w * 0.65, y0 + body_w * 0.5)], fill=GOLD)
    fx, fy = cx, y0 - 44 * SCALE
    d.polygon(
        [(fx, fy - 30 * SCALE), (fx + 14 * SCALE, fy + 4 * SCALE), (fx, fy + 16 * SCALE), (fx - 14 * SCALE, fy + 4 * SCALE)],
        fill=GOLD,
    )
    _rays(d, fx, fy - 4 * SCALE, 30 * SCALE, 52 * SCALE, 5, 3 * SCALE, GOLD_SOFT)


def _icon_globe(d: ImageDraw.ImageDraw, cx: int, top: int) -> None:
    cy = top + 120 * SCALE
    r = 54 * SCALE
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=GOLD, width=5 * SCALE)
    d.ellipse([cx - r * 0.45, cy - r, cx + r * 0.45, cy + r], outline=GOLD, width=4 * SCALE)
    d.line([cx - r, cy, cx + r, cy], fill=GOLD, width=4 * SCALE)
    d.line([cx - r * 0.86, cy - r * 0.5, cx + r * 0.86, cy - r * 0.5], fill=GOLD, width=3 * SCALE)
    d.line([cx - r * 0.86, cy + r * 0.5, cx + r * 0.86, cy + r * 0.5], fill=GOLD, width=3 * SCALE)
    _rays(d, cx, cy, r + 14 * SCALE, r + 38 * SCALE, 8, 3 * SCALE, GOLD_SOFT)


def _icon_bell(d: ImageDraw.ImageDraw, cx: int, top: int) -> None:
    y0 = top + 70 * SCALE
    d.pieslice([cx - 46 * SCALE, y0, cx + 46 * SCALE, y0 + 92 * SCALE], 180, 360, fill=GOLD)
    d.rectangle([cx - 46 * SCALE, y0 + 46 * SCALE, cx + 46 * SCALE, y0 + 92 * SCALE], fill=GOLD)
    d.polygon(
        [(cx - 54 * SCALE, y0 + 92 * SCALE), (cx + 54 * SCALE, y0 + 92 * SCALE), (cx + 40 * SCALE, y0 + 108 * SCALE), (cx - 40 * SCALE, y0 + 108 * SCALE)],
        fill=GOLD,
    )
    d.ellipse([cx - 9 * SCALE, y0 + 108 * SCALE, cx + 9 * SCALE, y0 + 124 * SCALE], fill=GOLD)
    d.ellipse([cx - 6 * SCALE, y0 - 16 * SCALE, cx + 6 * SCALE, y0 - 4 * SCALE], fill=GOLD)
    _rays(d, cx, y0 - 20 * SCALE, 14 * SCALE, 40 * SCALE, 5, 3 * SCALE, GOLD_SOFT)


ICONS = {
    "missa": _icon_chalice,
    "santos": _icon_halo,
    "padres": _icon_cross,
    "historia": _icon_book,
    "chosen": _icon_lamp,
    "mundo": _icon_globe,
    "noticias": _icon_bell,
    "velas": _icon_candle,
}


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


def make_post(
    category_key: str,
    eyebrow: str,
    title: str,
    subtitle: str,
    body: str,
    url: str,
    out_path: Path,
    background_art: str | None = None,
    background_crop: tuple[float, float, float, float] | None = None,
) -> None:
    if background_art:
        img = _photo_top_bg(background_art, background_crop)
    else:
        img = _radial_bg()
    d = ImageDraw.Draw(img)
    _draw_frame(d)

    if not background_art:
        icon_fn = ICONS.get(category_key, _icon_candle)
        icon_fn(d, W // 2, int(H * 0.075))

    f_eyebrow = font("EBGaramond.ttf", 22, 600)
    f_title = font("PlayfairDisplay.ttf", 58, 800)
    f_subtitle = font("EBGaramond.ttf", 27, 500)
    f_body = font("EBGaramond.ttf", 29, 450)
    f_url = font("PlayfairDisplay.ttf", 27, 700)

    y = int(H * 0.415)
    spaced_eyebrow = " ".join(list(eyebrow.upper()))
    tw = d.textlength(spaced_eyebrow, font=f_eyebrow)
    d.text(((W - tw) / 2, y), spaced_eyebrow, font=f_eyebrow, fill=GOLD_SOFT)
    y += 58 * SCALE

    title_lines = _wrap(d, title, f_title, W - 200 * SCALE)
    if len(title_lines) > 3:
        title_lines = title_lines[:3]
    for line in title_lines:
        tw = d.textlength(line, font=f_title)
        d.text(((W - tw) / 2, y), line, font=f_title, fill=GOLD)
        y += 74 * SCALE
    y += 4 * SCALE

    subtitle_lines = _wrap(d, subtitle, f_subtitle, W - 260 * SCALE)
    for line in subtitle_lines[:2]:
        tw = d.textlength(line, font=f_subtitle)
        d.text(((W - tw) / 2, y), line, font=f_subtitle, fill=CREAM)
        y += 44 * SCALE
    y += 14 * SCALE

    line_w = 90 * SCALE
    d.line([(W - line_w) / 2, y, (W + line_w) / 2, y], fill=GOLD_SOFT, width=2 * SCALE)
    y += 50 * SCALE

    body_lines = _wrap(d, body, f_body, W - 300 * SCALE)
    max_body_lines = 7
    if len(body_lines) > max_body_lines:
        body_lines = body_lines[:max_body_lines]
        body_lines[-1] = body_lines[-1].rstrip(".") + "…"
    for line in body_lines:
        tw = d.textlength(line, font=f_body)
        d.text(((W - tw) / 2, y), line, font=f_body, fill=CREAM)
        y += 46 * SCALE

    y += 18 * SCALE
    d.line([(W - line_w) / 2, y, (W + line_w) / 2, y], fill=GOLD_SOFT, width=2 * SCALE)
    y += 46 * SCALE

    tw = d.textlength(url, font=f_url)
    d.text(((W - tw) / 2, y), url, font=f_url, fill=GOLD)
    y += 48 * SCALE

    draw_logo_mark(d, W / 2, y + 28 * SCALE, r=26)

    final = img.resize((1080, 1350), Image.LANCZOS)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    final.save(out_path)
