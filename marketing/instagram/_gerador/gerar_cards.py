# -*- coding: utf-8 -*-
"""Gera as imagens de cena (Reels) e de slide (Stories) — mesma identidade
bordô/dourada dos posts, com o selo do Compêndio Católico em toda imagem.

Cobre TODAS as cenas de TODOS os roteiros: nenhuma categoria de publicação
fica só com texto, sempre tem uma imagem pronta pra postar ou editar.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cards import make_scene_card, make_story_slide_card

REELS_DIR = Path(__file__).resolve().parent.parent / "reels"
STORIES_DIR = Path(__file__).resolve().parent.parent / "stories"

# Cada reel: pasta, e uma lista de cenas (tempo, texto de tela, nota visual).
REELS = {
    "01-por-que-o-padre-levanta-a-hostia": [
        ("0–3s", "Por que o padre faz ISSO na missa?", "Filme a elevação da hóstia numa missa, de longe/de lado, sem focar rostos — ou use este card."),
        ("3–9s", "Na Idade Média, quase ninguém comungava toda semana.", "Card de texto, fundo neutro."),
        ("9–15s", 'Erguer a hóstia bem alto era a forma de todos poderem "ver a Deus".', "Volta ao clipe da elevação, se filmou."),
        ("15–18s", "Hoje é tradição — nasceu de um motivo bem humano ✝️", "Encerramento com a marca."),
    ],
    "02-sao-francisco-estigmas": [
        ("0–3s", "Isso aconteceu de verdade, em 1224 😮", "Arte sacra de São Francisco (Wikimedia Commons) com zoom lento, se tiver."),
        ("3–10s", "São Francisco de Assis foi a 1ª pessoa registrada na história a receber os estigmas.", "Card de texto."),
        ("10–16s", "As marcas das 5 chagas de Cristo, no próprio corpo dele.", "Card de texto."),
        ("16–20s", "Aconteceu 2 anos antes de sua morte.", "Encerramento com a marca."),
    ],
    "03-santo-dos-millennials": [
        ("0–3s", "Ele tinha 11 anos e já fazia ISSO 💻🙏", "Tela do site do Compêndio, ou foto oficial de Carlo Acutis."),
        ("3–10s", "Carlo Acutis catalogou milagres eucarísticos do mundo inteiro num site — feito por ELE.", "Card de texto."),
        ("10–16s", '"A Eucaristia é minha autoestrada para o céu." Morreu aos 15, de leucemia.', "Card de texto."),
        ("16–20s", 'O "santo dos millennials".', "Encerramento com a marca."),
    ],
    "04-capela-sistina": [
        ("0–3s", "4 anos. Praticamente sozinho. Olhando pra cima o tempo todo.", "Imagem do teto da Sistina, câmera olhando pra cima, se tiver."),
        ("3–10s", "Michelangelo pintou o teto da Capela Sistina entre 1508 e 1512.", "Card de texto."),
        ("10–16s", "Em pé, sobre andaimes, com o pescoço curvado pra trás.", "Card de texto."),
        ("16–18s", "Fé e esforço físico, juntos.", "Encerramento com a marca."),
    ],
    "05-the-chosen-crowdfunding": [
        ("0–3s", "A maior produção sobre Jesus já feita não veio de Hollywood.", "Card de texto autoral — sem cena da série."),
        ("3–10s", '"The Chosen" foi financiada, em boa parte, pelos próprios fãs.', "Card de texto."),
        ("10–15s", "Já assistiu? Qual foi sua cena favorita?", "Card de texto + pergunta."),
        ("15–18s", "Crowdfunding, temporada após temporada.", "Encerramento com a marca."),
    ],
    "06-jonathan-roumie-reza": [
        ("0–3s", "O ator que faz Jesus faz ISSO antes de cada cena.", "Card de texto — sem foto do ator sem licença."),
        ("3–10s", 'Jonathan Roumie reza antes das gravações de "The Chosen".', "Card de texto."),
        ("10–15s", "Em cenas mais fortes, já disse que se emociona de verdade, sem planejar.", "Card de texto."),
        ("15–18s", "Interpretar Jesus virou também jornada de fé pra ele.", "Encerramento com a marca."),
    ],
    "07-kobe-bryant-missa": [
        ("0–3s", "Uma curiosidade que emocionou o mundo em 2020.", "Card de texto, tom sóbrio."),
        ("3–10s", "Kobe Bryant, convertido ao catolicismo, foi à missa na manhã do dia em que morreu.", "Card de texto."),
        ("10–15s", "Um lembrete silencioso de como a fé estava presente no dia a dia dele.", "Card de texto."),
        ("15–18s", "Descanse em paz, Kobe.", "Encerramento com a marca."),
    ],
    "08-celtic-fc-frade": [
        ("0–3s", "Esse time de futebol nasceu de uma obra de caridade.", "Card de texto (evite reproduzir o escudo oficial)."),
        ("3–10s", "O Celtic FC foi fundado em 1887 por um frade marista.", "Card de texto."),
        ("10–15s", "Pra alimentar crianças pobres de famílias católicas imigrantes em Glasgow.", "Card de texto."),
        ("15–18s", "Futebol e caridade, desde o 1º apito.", "Encerramento com a marca."),
    ],
    "09-touchdown-jesus": [
        ("0–3s", 'Essa universidade tem um "Jesus" de olho no estádio.', "Foto do mural Touchdown Jesus, se tiver — ou este card."),
        ("3–10s", "Notre Dame, universidade católica dos EUA, fundada em 1842.", "Card de texto."),
        ("10–15s", 'O mural fica virado pro estádio — apelidado de "Touchdown Jesus".', "Card de texto."),
        ("15–18s", "Fé e tradição esportiva, lado a lado.", "Encerramento com a marca."),
    ],
    "10-tolkien-catolico": [
        ("0–3s", "O Senhor dos Anéis é mais católico do que você imagina 📚", "Card de texto autoral."),
        ("3–10s", "J.R.R. Tolkien, o autor, era católico devoto.", "Card de texto."),
        ("10–15s", '"Fundamentalmente uma obra religiosa e católica" — nas palavras dele mesmo.', "Card de texto."),
        ("15–18s", "Vai reler a trilogia com outros olhos?", "Encerramento com a marca."),
    ],
}

# Cada story: pasta, e uma lista de slides (kicker, texto grande, nota de sticker).
STORIES = {
    "01-quiz-de-sexta": [
        ("Quiz de sexta", "Quantos livros tem a Bíblia católica?", "Cole aqui o sticker de QUIZ: 66 / 70 / 73 / 80"),
        ("Resposta", "73! 46 no Antigo Testamento + 27 no Novo.", "Link do story pro post completo (#16)"),
        ("Todo sexta", "Acertou? Segue @compendiocatolico 🎯", "Sticker de link/menção"),
    ],
    "02-enquete-do-terco": [
        ("Enquete", "Você reza o terço?", "Cole aqui o sticker de ENQUETE: Sim / Ainda não"),
        ("Curiosidade", "O terço como rezamos hoje foi popularizado por São Domingos, no século 13.", ""),
        ("Convite", "Bora rezar 1 dezena junto agora?", "Sticker de caixinha de comentário/reação"),
    ],
    "03-contagem-regressiva-festa-de-santo": [
        ("Contagem regressiva", "Faltam poucos dias pro dia de Santo Antônio (13/06)", "Cole aqui o sticker de CONTAGEM REGRESSIVA"),
        ("No dia", "Feliz dia de Santo Antônio! 🕊️", "Sticker de menção — marca quem também é devoto"),
    ],
    "04-bastidores-do-compendio": [
        ("Bastidores", "Por trás do Compêndio Católico 👀", "Foto real da rotina/tela do site aqui"),
        ("Nosso processo", "Toda curiosidade é conferida em fonte confiável antes de ir pro ar.", ""),
        ("Call to action", "Link na bio pra explorar o acervo completo", "Sticker de link"),
    ],
    "05-caixinha-de-perguntas": [
        ("Pergunte", "Manda sua dúvida sobre fé, história da Igreja ou algum santo", "Cole aqui o sticker de PERGUNTA"),
        ("No dia seguinte", "Respondendo a pergunta de quem perguntou 👇", "Repost da pergunta recebida + resposta"),
    ],
    "06-enquete-the-chosen": [
        ("Enquete", "Qual apóstolo você mais gosta em The Chosen?", "Cole aqui o sticker de ENQUETE: Pedro 🐟 / Mateus 📜"),
        ("Curiosidade", "Um fato rápido sobre o apóstolo mais votado (ver post #30).", ""),
        ("Call to action", "Comenta se já maratonou a série toda 🙌", "Sticker de caixinha de comentário"),
    ],
}


def main() -> None:
    for slug, scenes in REELS.items():
        d = REELS_DIR / slug
        for i, (time, headline, note) in enumerate(scenes, start=1):
            make_scene_card(time, headline, note, d / f"cena-{i}.jpg")
        print("ok reel", slug, f"({len(scenes)} cenas)")

    for slug, slides in STORIES.items():
        d = STORIES_DIR / slug
        for i, (kicker, text, sticker_note) in enumerate(slides, start=1):
            make_story_slide_card(kicker, text, sticker_note, d / f"slide-{i}.jpg")
        print("ok story", slug, f"({len(slides)} slides)")


if __name__ == "__main__":
    main()
