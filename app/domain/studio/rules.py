"""Regras puras do estúdio: o que um reel e um pedido de vídeo precisam ter."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping

from app.domain.studio.entities import NewVideoRequest, Reel

# Os mesmos temas do filtro de /reels no site (lib/reels.ts).
REEL_THEMES: dict[str, str] = {
    "santos": "Santos",
    "maria": "Nossa Senhora",
    "anjos": "Anjos",
    "biblia": "Bíblia",
    "missa": "Missa e sacramentos",
    "doutrina": "Doutrina",
    "historia": "História da Igreja",
    "papas": "Papas",
    "igrejas": "Igrejas e devoções",
    "curiosidades": "Curiosidades",
}
# Cinema: pinturas em 3D, narrado. Catequese: o modelo Pergaminho do videos-py, narrado
# e didático. Objeção: uma objeção comum à fé e a resposta curta, sobre pinturas.
VIDEO_FORMATS = ("cinema", "catequese", "objecao")
# Só o modelo Cinema sincroniza uma gravação real; o Pergaminho (catequese) só tem voz sintética.
OWN_VOICE_FORMATS = ("cinema", "objecao")

_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_TITLE = 140
MAX_CAPTION = 2200  # o limite de legenda do Instagram
MAX_THEME = 200
MAX_NOTES = 2000


class ValidationError(ValueError):
    """Dado recusado; a mensagem vai para a tela do painel."""


def slugify(text: str) -> str:
    plain = (
        unicodedata.normalize("NFKD", text)
        .encode("ascii", "ignore")
        .decode("ascii")
        .casefold()
    )
    return re.sub(r"[^a-z0-9]+", "-", plain).strip("-")[:60].strip("-") or "video"


def _text(data: Mapping[str, object], key: str, *, limit: int, required: bool) -> str:
    value = data.get(key, "")
    if not isinstance(value, str):
        raise ValidationError(f"{key}: precisa ser texto.")
    value = value.strip()
    if required and not value:
        raise ValidationError(f"{key}: não pode ficar vazio.")
    if len(value) > limit:
        raise ValidationError(f"{key}: no máximo {limit} caracteres.")
    return value


def _url(data: Mapping[str, object], key: str) -> str:
    value = _text(data, key, limit=500, required=True)
    if not (value.startswith("https://") or value.startswith("/")) or value.startswith(
        "//"
    ):
        raise ValidationError(f"{key}: endereço inválido.")
    return value


def _theme(value: object) -> str:
    if value not in REEL_THEMES:
        raise ValidationError("tema: escolha um dos temas do site.")
    return str(value)


def _size(data: Mapping[str, object], key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 4096:
        raise ValidationError(f"{key}: tamanho inválido.")
    return value


def new_reel(data: Mapping[str, object]) -> Reel:
    slug = data.get("slug")
    if not isinstance(slug, str) or not _SLUG.match(slug) or len(slug) > 80:
        raise ValidationError("slug: só letras minúsculas, números e hífens.")
    return Reel(
        slug=slug,
        title=_text(data, "titulo", limit=MAX_TITLE, required=True),
        caption=_text(data, "legenda", limit=MAX_CAPTION, required=False),
        theme=_theme(data.get("tema")),
        width=_size(data, "largura"),
        height=_size(data, "altura"),
        video_url=_url(data, "video_url"),
        cover_url=_url(data, "capa_url"),
        published=bool(data.get("publicado", False)),
    )


def clean_reel_patch(data: Mapping[str, object]) -> dict[str, object]:
    """Campos que o painel pode mudar num reel; o slug (o endereço) não muda."""
    allowed = {"titulo", "legenda", "tema", "publicado"}
    unknown = set(data) - allowed
    if unknown:
        raise ValidationError(f"Não dá para mudar: {', '.join(sorted(unknown))}.")
    patch: dict[str, object] = {}
    if "titulo" in data:
        patch["title"] = _text(data, "titulo", limit=MAX_TITLE, required=True)
    if "legenda" in data:
        patch["caption"] = _text(data, "legenda", limit=MAX_CAPTION, required=False)
    if "tema" in data:
        patch["theme"] = _theme(data["tema"])
    if "publicado" in data:
        if not isinstance(data["publicado"], bool):
            raise ValidationError("publicado: sim ou não.")
        patch["published"] = data["publicado"]
    if not patch:
        raise ValidationError("Nada para mudar.")
    return patch


def new_request(data: Mapping[str, object]) -> NewVideoRequest:
    question = _text(data, "pergunta", limit=MAX_THEME, required=False)
    if question and not question.endswith("?"):
        raise ValidationError("pergunta: termine com ponto de interrogação.")
    video_format = data.get("formato", "cinema")
    if video_format not in VIDEO_FORMATS:
        raise ValidationError("formato: cinema, catequese ou objeção.")
    own_voice = data.get("voz_propria", False)
    if not isinstance(own_voice, bool):
        raise ValidationError("voz_propria: sim ou não.")
    if own_voice and video_format not in OWN_VOICE_FORMATS:
        raise ValidationError("Voz própria só no Cinema e na Objeção.")
    return NewVideoRequest(
        theme=_text(data, "tema", limit=MAX_THEME, required=True),
        question=question,
        notes=_text(data, "notas", limit=MAX_NOTES, required=False),
        format=str(video_format),
        own_voice=own_voice,
    )
