"""Caminho da Santidade: uma trilha de casas, como as lições de um curso, que a pessoa
percorre uma por vez fazendo a tarefa de cada casa.

As três vias são as da tradição da vida espiritual (São Boaventura, "De triplici via";
Garrigou-Lagrange, "As três idades da vida interior"): a purgativa, de conversão e
combate ao pecado; a iluminativa, de crescimento nas virtudes; e a unitiva, de união
com Deus. No fim da trilha está a santidade, a que todos são chamados (Lumen Gentium,
40; Catecismo, § 2013).

As tarefas são as práticas do dia do perfil e as lições da Academia da Fé. Uma casa de
prática pede a prática marcada hoje; a mesma marcação não move duas casas.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from typing import Literal

from app.domain.profiles.entities import ACTIVITIES

ViaId = Literal["purgativa", "iluminativa", "unitiva"]


class PathError(Exception):
    """A casa pedida não pode ser concluída agora; a mensagem diz por quê."""


@dataclass(frozen=True)
class Via:
    id: ViaId
    name: str
    description: str


@dataclass(frozen=True)
class House:
    number: int
    via: ViaId
    title: str
    text: str
    # "atividade": `task` é o id da prática do dia. "licao": `lessons_needed` lições.
    kind: Literal["atividade", "licao"]
    task: str
    lessons_needed: int = 0


VIAS: tuple[Via, ...] = (
    Via(
        "purgativa",
        "Via Purgativa",
        "O começo: voltar-se para Deus, pedir perdão e lutar contra o pecado.",
    ),
    Via(
        "iluminativa",
        "Via Iluminativa",
        "O crescimento: a luz da Palavra e dos sacramentos forma as virtudes.",
    ),
    Via(
        "unitiva",
        "Via Unitiva",
        "A união: a vida inteira se torna oração e amor a Deus e ao próximo.",
    ),
)

# (via, título, chamada, tarefa). "licao" é uma lição da Academia; o resto, práticas.
_TRILHA: tuple[tuple[ViaId, str, str, str], ...] = (
    ("purgativa", "O chamado", "Tudo começa com um tempo a sós com Deus.", "oracao_livre"),
    ("purgativa", "A Palavra", "Leia um capítulo dos Evangelhos.", "leitura_biblica"),
    ("purgativa", "Aprender a fé", "Não se ama o que não se conhece.", "licao"),
    ("purgativa", "O abraço do Pai", "Volte para casa no sacramento do perdão.", "confissao"),
    ("purgativa", "Com Maria", "Reze o Terço com a Mãe de Jesus.", "terco"),
    ("purgativa", "O deserto", "Um pequeno jejum ensina o coração a ter fome de Deus.", "jejum"),
    ("purgativa", "O banquete", "Participe da Santa Missa.", "missa"),
    ("purgativa", "Raízes", "Mais uma lição para firmar a fé.", "licao"),
    ("purgativa", "As mãos de Cristo", "Faça uma obra de misericórdia.", "caridade"),
    ("purgativa", "Silêncio", "Ore em silêncio, sem pressa.", "oracao_livre"),
    ("purgativa", "Perseverança", "Reze um dia de novena ao seu santo.", "novena"),
    ("purgativa", "Diante dEle", "Fique um tempo diante do Santíssimo.", "adoracao"),
    ("iluminativa", "A luz da Palavra", "Deixe a Escritura iluminar o seu dia.", "leitura_biblica"),
    ("iluminativa", "Conhecer para amar", "Uma lição da Academia da Fé.", "licao"),
    ("iluminativa", "O Dia do Senhor", "A Missa no centro da semana.", "missa"),
    ("iluminativa", "Contemplar os mistérios", "O Terço, mistério por mistério.", "terco"),
    ("iluminativa", "Obras de misericórdia", "Sirva alguém que precisa.", "caridade"),
    ("iluminativa", "As virtudes", "Mais uma lição para crescer.", "licao"),
    ("iluminativa", "Amizade com Jesus", "Adore o Senhor presente na Eucaristia.", "adoracao"),
    ("iluminativa", "Domínio de si", "Jejue por amor, não por regra.", "jejum"),
    ("iluminativa", "Os amigos de Deus", "Peça a ajuda dos santos numa novena.", "novena"),
    ("iluminativa", "Sabedoria", "Uma lição sobre a fé que você professa.", "licao"),
    ("iluminativa", "Recomeçar", "A confissão frequente faz crescer na graça.", "confissao"),
    ("iluminativa", "Comunhão", "Receba o Senhor na Missa.", "missa"),
    ("unitiva", "Morada de Deus", "Adoração: estar com quem nos ama.", "adoracao"),
    ("unitiva", "Palavra viva", "Leia a Bíblia como quem conversa.", "leitura_biblica"),
    ("unitiva", "Doutrina e vida", "Uma lição para unir fé e vida.", "licao"),
    ("unitiva", "Rosário de amor", "Reze o Terço pelas intenções do mundo.", "terco"),
    ("unitiva", "Amar como Ele amou", "Faça o bem sem que ninguém saiba.", "caridade"),
    ("unitiva", "Uma só carne", "Viva a Missa por inteiro.", "missa"),
    ("unitiva", "Oferta", "Ofereça um jejum por alguém.", "jejum"),
    ("unitiva", "Plenitude", "A última lição desta trilha.", "licao"),
    ("unitiva", "Oração do coração", "Reze em qualquer lugar, a qualquer hora.", "oracao_livre"),
    ("unitiva", "Comunhão dos santos", "Uma novena com toda a Igreja.", "novena"),
    ("unitiva", "Coração puro", "A confissão que prepara a festa.", "confissao"),
    ("unitiva", "Santidade", "A Missa que abre o céu. Bem-vindo ao fim da trilha!", "missa"),
)


def _build() -> tuple[House, ...]:
    houses: list[House] = []
    lessons = 0
    for number, (via, title, text, task) in enumerate(_TRILHA, start=1):
        if task == "licao":
            lessons += 1
            houses.append(House(number, via, title, text, "licao", "licao", lessons))
        else:
            houses.append(House(number, via, title, text, "atividade", task))
    return tuple(houses)


HOUSES: tuple[House, ...] = _build()
_ACTIVITY_NAMES: dict[str, str] = {activity.id: activity.name for activity in ACTIVITIES}


def task_name(h: House) -> str:
    return "Lição da Academia da Fé" if h.kind == "licao" else _ACTIVITY_NAMES[h.task]


def house(number: int) -> House:
    if not 1 <= number <= len(HOUSES):
        raise PathError(f"A trilha vai da casa 1 à {len(HOUSES)}.")
    return HOUSES[number - 1]


def houses_done(steps: Iterable[tuple[int, date]]) -> int:
    """Casas concluídas em sequência, a partir da primeira."""
    done = {number for number, _ in steps}
    count = 0
    while count + 1 in done:
        count += 1
    return count


def check_advance(
    number: int,
    *,
    steps: Iterable[tuple[int, date]],
    last_activity_days: Mapping[str, date],
    lessons_count: int,
    today: date,
) -> House:
    """A casa que pode ser concluída agora, ou `PathError` com o motivo."""
    steps = list(steps)
    target = house(number)
    current = houses_done(steps) + 1
    if number < current:
        raise PathError("Esta casa já foi concluída.")
    if number > current:
        raise PathError(f"Siga a trilha: a próxima é a casa {current}.")
    if target.kind == "licao":
        if lessons_count < target.lessons_needed:
            raise PathError("Conclua mais uma lição da Academia da Fé para avançar.")
        return target
    if last_activity_days.get(target.task) != today:
        raise PathError(f"Marque hoje a prática: {_ACTIVITY_NAMES[target.task]}.")
    used_today = {house(n).task for n, day in steps if day == today}
    if target.task in used_today:
        raise PathError("Esta prática já moveu uma casa hoje. Volte amanhã para seguir.")
    return target
