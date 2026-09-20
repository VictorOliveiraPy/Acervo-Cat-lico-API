# -*- coding: utf-8 -*-
"""Regenera os carrosséis de marketing/instagram/historias/."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from historias import make_cover_slide, make_cta_slide, make_text_slide

OUT = Path(__file__).resolve().parent.parent / "historias"


def filho_prodigo() -> None:
    d = OUT / "filho-prodigo"
    make_cover_slide("filho_prodigo", "uma história para refletir", "O Filho Pródigo", "arraste para ler →", d / "1-capa.jpg", 0, 5)
    make_text_slide(
        "Parte 2 de 5",
        "Um jovem pediu ao pai a herança antes da hora — e foi embora viver longe de tudo que conhecia. "
        "Gastou tudo. Até cuidar de porcos, o trabalho mais humilhante para um judeu da época, pareceu "
        "melhor que voltar pra casa com vergonha.",
        d / "2.jpg", 1, 5,
    )
    make_text_slide(
        "Parte 3 de 5",
        "Mas ele voltou. Ensaiou um pedido de perdão o caminho inteiro. Não esperava festa — só um lugar "
        "de servo. O pai, porém, o viu ainda de longe... e correu.",
        d / "3.jpg", 2, 5,
    )
    make_text_slide(
        "Parte 4 de 5",
        'Correr não era gesto de homem importante — mas o amor do pai não se importou com isso. '
        '"Este meu filho estava morto e voltou à vida" (Lc 15,24). Não importa o quanto você se afastou: '
        "Ele corre em sua direção assim que você volta.",
        d / "4.jpg", 3, 5,
    )
    make_cta_slide(
        "Leia a parábola completa (Lucas 15, 11-32) e mais sobre as parábolas de Jesus em",
        "compendio-catolico.com", d / "5-cta.jpg", 4, 5,
    )


def paixao_em_4_atos() -> None:
    d = OUT / "paixao-em-4-atos"
    make_cover_slide("cruz", "sexta-feira santa", "A Paixão em 4 atos", "arraste para ler →", d / "1-capa.jpg", 0, 6)
    make_text_slide(
        "1. Getsêmani",
        'Na noite antes de morrer, Jesus suou sangue de angústia (Lc 22,44) e pediu: "Se possível, afaste '
        'de mim este cálice; mas não seja como eu quero, e sim como queres tu" (Mt 26,39).',
        d / "2.jpg", 1, 6,
    )
    make_text_slide(
        "2. A condenação",
        "Diante de Pilatos, coroado de espinhos e chamado de rei como zombaria, Jesus não abriu a boca "
        "para se defender (Is 53,7; Mt 27,29).",
        d / "3.jpg", 2, 6,
    )
    make_text_slide(
        "3. O calvário",
        'Carregou a própria cruz até o Gólgota. "Pai, perdoa-lhes, porque não sabem o que fazem" '
        "(Lc 23,34) — mesmo ali, perdão.",
        d / "4.jpg", 3, 6,
        background_art="ecce_homo",
        background_crop=(0.17, 0.155, 0.865, 0.86),
    )
    make_text_slide(
        "4. O terceiro dia",
        '"Ele não está aqui; ressuscitou, como tinha dito" (Mt 28,6). A cruz não foi o fim da história.',
        d / "5.jpg", 4, 6,
    )
    make_cta_slide(
        "Mais sobre a Semana Santa e a liturgia do ano todo em",
        "compendio-catolico.com", d / "6-cta.jpg", 5, 6,
    )


if __name__ == "__main__":
    filho_prodigo()
    paixao_em_4_atos()
    print("ok")
