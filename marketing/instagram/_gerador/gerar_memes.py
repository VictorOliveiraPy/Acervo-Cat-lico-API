# -*- coding: utf-8 -*-
"""Regenera os memes de marketing/instagram/memes/. Rode depois de editar as
legendas abaixo ou trocar alguma obra em arte/ (ver SOURCES.md pra créditos)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from memes import make_meme

OUT = Path(__file__).resolve().parent.parent / "memes"

JOBS = [
    ("thomas", "Quando você diz que rezou o terço inteirinho em 3 minutos", "bottom", None, "meme-01-thomas.jpg"),
    ("mateus", "Quando o padre pergunta quem quer fazer a leitura hoje", "bottom", None, "meme-02-mateus.jpg"),
    ("cristo_face", "Quando alguém começa a fofocar na saída da missa", "bottom", None, "meme-03-cristoface.jpg"),
    ("tentacao", "Vem me tentar agora, capeta!", "bottom", None, "meme-04-tentacao.jpg"),
    ("emaus", "Quando descobre quem comeu o último pão de queijo da festa junina da paróquia", "bottom", None, "meme-05-emaus.jpg"),
    ("madonna", 'Eu esperando o padre falar "vamos concluir" pela 3ª vez', "bottom", (0.15, 0.78, 0.85, 1.0), "meme-06-madonna.jpg"),
    ("cruz", "Toda cruz que você carrega, Ele carregou primeiro.", "top", None, "meme-07-cruz.jpg"),
    ("ecce_homo", "Antes de reclamar do seu dia, lembra do que Ele passou pelo seu.", "top", None, "meme-08-eccehomo.jpg"),
]

if __name__ == "__main__":
    for art, caption, pos, crop, name in JOBS:
        make_meme(art, caption, OUT / name, position=pos, crop_box=crop)
        print("ok", name)
