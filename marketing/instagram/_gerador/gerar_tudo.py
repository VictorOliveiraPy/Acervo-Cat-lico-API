# -*- coding: utf-8 -*-
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from identidade import make_post
from dados import CATS, POSTS

OUT_ROOT = Path(__file__).resolve().parent.parent / "posts"

# Foto de fundo real por post (n -> (chave em arte/, crop opcional l,t,r,b).
# Sem entrada aqui = cai no icone abstrato antigo (nao deveria sobrar nenhum).
ART_MAP: dict[int, tuple[str, tuple[float, float, float, float] | None]] = {
    1: ("ceia", None),
    2: ("incenso", None),
    3: ("eucaristia_ostensorio", None),
    4: ("sino", None),
    5: ("liturgia_oriental", None),
    6: ("teresinha", None),
    7: ("judas_tadeu", None),
    8: ("santo_agostinho", None),
    9: ("francisco_estigmas", None),
    10: ("monstrancia", None),
    11: ("antonio", None),
    12: ("mateus", None),
    13: ("liturgia_oriental", None),
    14: ("coroinhas", None),
    15: ("vianney", None),
    16: ("biblia", None),
    17: ("niceia", None),
    18: ("vaticano_aereo", None),
    19: ("teto_afresco", None),
    20: ("bento_xvi", None),
    21: ("tentacao", None),
    22: ("bolonha", None),
    23: ("cinema", None),
    24: ("jonathan_roumie", None),
    25: ("cinema", None),
    26: ("manuscrito_hebraico", None),
    27: ("missal_velas", None),
    28: ("mapa_mundo", None),
    29: ("galileia", None),
    30: ("galileia", None),
    31: ("ronaldo", None),
    32: ("messi", (0.42, 0.50, 0.82, 0.96)),
    33: ("kobe_bryant", None),
    34: ("bocelli", None),
    35: ("livros_antigos", None),
    36: ("scorsese", (0.0, 0.0, 1.0, 0.82)),
    37: ("walfrid", None),
    38: ("touchdown_jesus", None),
    39: ("basilica_sao_pedro", None),
    40: ("basilica_sao_pedro", None),
    41: ("basilica_sao_pedro", None),
    42: ("basilica_sao_pedro", None),
    43: ("basilica_sao_pedro", None),
    44: ("basilica_sao_pedro", None),
}


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text[:60].rstrip("-")


def main() -> None:
    for post in POSTS:
        cat = post["cat"]
        cat_info = CATS[cat]
        slug = slugify(post["hook"])
        base_name = f"{post['n']:02d}-{slug}"
        cat_dir = OUT_ROOT / cat
        cat_dir.mkdir(parents=True, exist_ok=True)

        art_key, art_crop = ART_MAP.get(post["n"], (None, None))

        png_path = cat_dir / f"{base_name}.png"
        make_post(
            category_key=cat,
            eyebrow=cat_info["label"],
            title=post["hook"],
            subtitle=cat_info["kicker"],
            body=post["fact"],
            url="compendio-catolico.com",
            out_path=png_path,
            background_art=art_key,
            background_crop=art_crop,
        )

        md_path = cat_dir / f"{base_name}.md"
        md_content = f"""# {post['n']:02d}. {post['hook']}

**Categoria:** {cat_info['label']}
**Imagem:** `{base_name}.png`

## Legenda (pronta pra copiar)

{post['caption']}

## Hashtags

{post['tags']}

## Sugestão de foto/arte alternativa

{post['photo']}
"""
        md_path.write_text(md_content, encoding="utf-8")
        print("ok", base_name)


if __name__ == "__main__":
    main()
