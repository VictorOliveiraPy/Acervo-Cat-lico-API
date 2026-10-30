"""Temas do acervo: as tags das entradas, reunidas sob um slug único.

As tags são texto livre, então a mesma ideia aparece como "Batismo" e "batismo",
ou "Bispo" e "bispos". O slug une o que só difere em caixa ou acento, e
`_SYNONYMS` une o singular e o plural que significam a mesma coisa. A regra de
plural não é automática de propósito: ela juntaria "Sinai" com "sinais".
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter

_SYNONYMS = {
    "apostolo": "apostolos",
    "bispo": "bispos",
    "coroinha": "coroinhas",
    "deuterocanonico": "deuterocanonicos",
    "diacono": "diaconos",
    "evangelho": "evangelhos",
    "hino": "hinos",
    "icone": "icones",
    "milagre": "milagres",
    "paroco": "parocos",
    "patriarca": "patriarcas",
    "reliquia": "reliquias",
    "sacramento": "sacramentos",
    "solenidade": "solenidades",
    "vela": "velas",
}


def _slugify(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    ascii_only = decomposed.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", ascii_only).strip("-")


def theme_slug(tag: str) -> str:
    """Slug do tema de uma tag; vazio quando a tag não tem letra nem número."""
    slug = _slugify(tag)
    return _SYNONYMS.get(slug, slug)


def theme_name(variants: Counter[str], slug: str) -> str:
    """Nome de exibição: a grafia mais usada, preferindo a do próprio slug."""
    own = Counter({tag: count for tag, count in variants.items() if _slugify(tag) == slug})
    pool = own or variants
    name = min(pool, key=lambda tag: (-pool[tag], tag))
    return name[0].upper() + name[1:]
