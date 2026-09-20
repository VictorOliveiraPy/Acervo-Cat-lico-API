# -*- coding: utf-8 -*-
"""Regenera os memes de marketing/instagram/memes/. Rode depois de editar as
legendas abaixo ou trocar alguma obra em arte/ (ver SOURCES.md pra créditos)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from memes import make_meme

OUT = Path(__file__).resolve().parent.parent / "memes"

JOBS = [
    ("thomas", "Quando sua mãe pede prova que você foi mesmo à missa de domingo", "bottom", None, "meme-01-thomas.jpg"),
    ("mateus", "Quando o padre pergunta quem topa ser catequista esse ano", "bottom", None, "meme-02-mateus.jpg"),
    ("cristo_face", "Quando você jura que não vai fofocar, mas alguém manda o áudio de 10 minutos", "bottom", None, "meme-03-cristoface.jpg"),
    ("tentacao", "Vem me tentar agora, capeta!", "bottom", None, "meme-04-tentacao.jpg"),
    ("emaus", "Quando descobre quem comeu escondido o último salgadinho da festa da paróquia", "bottom", None, "meme-05-emaus.jpg"),
    ("madonna", 'Eu esperando o padre falar "vamos concluir" pela 3ª vez', "bottom", (0.15, 0.78, 0.85, 1.0), "meme-06-madonna.jpg"),
    ("filho_prodigo", "Voltando pra casa dos pais depois de gastar o salário todo no mês", "bottom", None, "meme-07-filhoprodigo.jpg"),
    ("cruz", "Toda cruz que você carrega, Ele carregou primeiro.", "top", None, "meme-08-cruz.jpg"),
    ("ecce_homo", "Antes de reclamar do seu dia, lembra do que Ele passou pelo seu.", "top", None, "meme-09-eccehomo.jpg"),
]

if __name__ == "__main__":
    for art, caption, pos, crop, name in JOBS:
        make_meme(art, caption, OUT / name, position=pos, crop_box=crop)
        print("ok", name)
