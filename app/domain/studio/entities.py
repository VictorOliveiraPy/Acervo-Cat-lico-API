"""Entidades do estúdio: o reel (vídeo no site) e o pedido de vídeo novo."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

RequestStatus = Literal["na_fila", "gerando", "aguardando_voz", "pronto", "erro", "cancelado"]


@dataclass(frozen=True)
class Reel:
    slug: str
    title: str
    caption: str
    theme: str
    width: int
    height: int
    video_url: str
    cover_url: str
    published: bool = False
    created_at: datetime | None = None


@dataclass(frozen=True)
class NewVideoRequest:
    theme: str
    question: str
    notes: str
    format: str
    # Narrado com a voz gravada de quem administra, em vez da voz sintética.
    own_voice: bool = False


@dataclass
class VideoRequest:
    id: int
    theme: str
    question: str
    notes: str
    format: str
    status: RequestStatus = "na_fila"
    # O que o gerador está fazendo agora ("Escrevendo o roteiro", "Renderizando 40%").
    stage: str = ""
    progress: int = 0
    error: str = ""
    slug: str | None = None
    own_voice: bool = False
    # O texto que a pessoa grava (abertura e falas, na ordem), quando `own_voice`.
    script: str = ""
    voice_url: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    extra: dict[str, object] = field(default_factory=dict)
