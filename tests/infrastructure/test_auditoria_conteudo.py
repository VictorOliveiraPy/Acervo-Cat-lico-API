"""Linhas do `content-audit.csv`, a partir do acervo real."""

from __future__ import annotations

from app.infrastructure.acervo.json_repository import Repository
from scripts.gerar_auditoria_conteudo import COLUNAS, linhas


def test_should_cover_every_entry_sorted_by_word_count() -> None:
    repo = Repository()
    repo.load()
    entries = repo.all_entries()

    result = linhas(entries)

    assert len(result) == len(entries)
    assert all(set(linha) == set(COLUNAS) for linha in result)
    counts = [linha["palavras"] for linha in result]
    assert counts == sorted(counts)
    assert counts[-1] > 0
