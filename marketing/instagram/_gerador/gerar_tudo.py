# -*- coding: utf-8 -*-
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from identidade import make_post
from dados import CATS, POSTS

OUT_ROOT = Path(__file__).resolve().parent.parent / "posts"


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

        png_path = cat_dir / f"{base_name}.png"
        make_post(
            category_key=cat,
            eyebrow=cat_info["label"],
            title=post["hook"],
            subtitle=cat_info["kicker"],
            body=post["fact"],
            url="compendio-catolico.com",
            out_path=png_path,
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
