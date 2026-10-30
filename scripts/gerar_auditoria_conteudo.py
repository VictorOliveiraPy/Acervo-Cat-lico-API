"""Gera `content-audit.csv`: tamanho e estrutura de cada entrada, da menor para a maior.

Mostra onde falta conteúdo, sem escrever nenhum:

    python scripts/gerar_auditoria_conteudo.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.infrastructure.acervo.json_repository import Repository  # noqa: E402
from app.models import AnyEntry  # noqa: E402

DESTINO = ROOT / "content-audit.csv"
COLUNAS = ("slug", "categoria", "palavras", "tem_oracao", "tem_faq", "tem_imagem", "dateModified")


def _textos(entry: AnyEntry) -> list[str]:
    return [
        entry.corpo,
        getattr(entry, "texto", None) or "",
        entry.oracao or "",
        entry.iconografia or "",
        *entry.frases,
        *entry.curiosidades,
        *(secao.texto for secao in entry.biografia),
        *(f"{item.pergunta} {item.resposta}" for item in entry.faq),
    ]


def _sim_nao(valor: object) -> str:
    return "sim" if valor else "nao"


def linhas(entries: list[AnyEntry]) -> list[dict[str, str | int]]:
    """Uma linha por entrada, com a de menos palavras primeiro."""
    resultado: list[dict[str, str | int]] = [
        {
            "slug": entry.slug,
            "categoria": entry.categoria.value,
            "palavras": sum(len(texto.split()) for texto in _textos(entry)),
            "tem_oracao": _sim_nao(entry.oracao or getattr(entry, "texto", None)),
            "tem_faq": _sim_nao(entry.faq),
            "tem_imagem": _sim_nao(entry.imagem),
            "dateModified": entry.atualizado_em.isoformat() if entry.atualizado_em else "",
        }
        for entry in entries
    ]
    return sorted(resultado, key=lambda linha: (linha["palavras"], linha["categoria"], linha["slug"]))


def main() -> None:
    repo = Repository()
    repo.load()
    conteudo = linhas(repo.all_entries())
    with DESTINO.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=COLUNAS)
        escritor.writeheader()
        escritor.writerows(conteudo)
    print(f"{DESTINO.name}: {len(conteudo)} entradas")


if __name__ == "__main__":
    main()
