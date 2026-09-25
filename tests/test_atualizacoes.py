"""Manifesto de datas de atualização: script (git) e injeção na carga."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import date
from pathlib import Path

import pytest

from app.core.exceptions import DataIntegrityError
from app.infrastructure.acervo.json_repository import Repository
from app.models import Category
from scripts.gerar_atualizacoes import assinatura, gerar, ultimas_alteracoes

GLOSSARIO_REAL = Path(__file__).resolve().parents[1] / "app" / "data" / "glossario.json"


def _item(slug: str, corpo: str = "texto") -> dict:
    return {"slug": slug, "titulo": slug, "corpo": corpo}


# --------------------------------------------------------------------------- lógica pura


def test_should_date_each_entry_by_its_last_content_change() -> None:
    versoes = [
        ("2026-01-01", {"a": _item("a"), "b": _item("b")}),
        ("2026-02-01", {"a": _item("a"), "b": _item("b", "novo")}),
        ("2026-03-01", {"a": _item("a"), "b": _item("b", "novo"), "c": _item("c")}),
    ]

    assert ultimas_alteracoes(versoes) == {"a": "2026-01-01", "b": "2026-02-01", "c": "2026-03-01"}


def test_should_drop_entries_that_no_longer_exist() -> None:
    versoes = [("2026-01-01", {"a": _item("a"), "b": _item("b")}), ("2026-02-01", {"a": _item("a")})]

    assert ultimas_alteracoes(versoes) == {"a": "2026-01-01"}


def test_should_ignore_the_atualizado_em_field_itself_when_comparing_content() -> None:
    assert assinatura({**_item("a"), "atualizado_em": "2026-05-05"}) == assinatura(_item("a"))
    assert ultimas_alteracoes([]) == {}


# --------------------------------------------------------------------------- git de verdade


def _git(cwd: Path, *args: str, dia: str | None = None) -> None:
    env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull}
    if dia:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = f"{dia}T12:00:00+00:00"
    subprocess.run(  # noqa: S603 - o teste roda o git de propósito, num repositório temporário
        ["git", "-C", str(cwd), "-c", "user.name=t", "-c", "user.email=t@t", *args],  # noqa: S607
        check=True,
        capture_output=True,
        env=env,
    )


def _grava(root: Path, itens: list[dict]) -> None:
    arquivo = root / "app" / "data" / "glossario.json"
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    arquivo.write_text(json.dumps({"_meta": {"categoria": "glossario"}, "itens": itens}), encoding="utf-8")


def test_should_read_dates_from_git_history_and_use_today_for_uncommitted_changes(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q")
    _grava(tmp_path, [_item("a"), _item("b")])
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "1", dia="2026-01-10")
    _grava(tmp_path, [_item("a"), _item("b", "mudou")])
    _git(tmp_path, "commit", "-q", "-am", "2", dia="2026-02-20")
    _grava(tmp_path, [_item("a", "editado sem commit"), _item("b", "mudou")])

    manifesto = gerar(tmp_path, date(2026, 9, 25))

    assert manifesto == {"glossario": {"a": "2026-09-25", "b": "2026-02-20"}}


def test_should_not_count_json_reformatting_as_a_content_change(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q")
    _grava(tmp_path, [_item("a")])
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "1", dia="2026-01-10")
    arquivo = tmp_path / "app" / "data" / "glossario.json"
    arquivo.write_text(json.dumps(json.loads(arquivo.read_text()), indent=4), encoding="utf-8")
    _git(tmp_path, "commit", "-q", "-am", "reformata", dia="2026-03-30")

    assert gerar(tmp_path, date(2026, 9, 25)) == {"glossario": {"a": "2026-01-10"}}


# --------------------------------------------------------------------------- carga


def _dados(tmp_path: Path, itens: list[dict]) -> Path:
    meta = json.loads(GLOSSARIO_REAL.read_text(encoding="utf-8"))["_meta"]
    (tmp_path / "glossario.json").write_text(json.dumps({"_meta": meta, "itens": itens}), encoding="utf-8")
    return tmp_path


def _termo(slug: str, **extra: str) -> dict:
    return {"id": f"glossario:{slug}", "slug": slug, "titulo": slug.title(), "categoria": "glossario",
            "resumo": "r", "corpo": "c", **extra}


def _carrega(data_dir: Path) -> Repository:
    repo = Repository(data_dir, strict=False)
    repo.load()
    return repo


def test_should_inject_the_manifest_date_into_the_entry(tmp_path: Path) -> None:
    _dados(tmp_path, [_termo("graca"), _termo("fe")])
    (tmp_path / "atualizacoes.json").write_text(json.dumps({"glossario": {"graca": "2026-09-20"}}), encoding="utf-8")

    repo = _carrega(tmp_path)

    assert repo.get_by_slug(Category.GLOSSARIO, "graca").atualizado_em == date(2026, 9, 20)
    assert repo.get_by_slug(Category.GLOSSARIO, "fe").atualizado_em is None


def test_should_work_without_a_manifest_and_let_an_explicit_date_win(tmp_path: Path) -> None:
    _dados(tmp_path, [_termo("graca", atualizado_em="2026-01-01")])

    assert _carrega(tmp_path).get_by_slug(Category.GLOSSARIO, "graca").atualizado_em == date(2026, 1, 1)

    (tmp_path / "atualizacoes.json").write_text(json.dumps({"glossario": {"graca": "2026-09-20"}}), encoding="utf-8")
    assert _carrega(tmp_path).get_by_slug(Category.GLOSSARIO, "graca").atualizado_em == date(2026, 1, 1)


def test_should_fail_loudly_on_a_broken_manifest(tmp_path: Path) -> None:
    _dados(tmp_path, [_termo("graca")])

    (tmp_path / "atualizacoes.json").write_text("{quebrado", encoding="utf-8")
    with pytest.raises(DataIntegrityError):
        _carrega(tmp_path)

    (tmp_path / "atualizacoes.json").write_text(json.dumps({"glossario": {"graca": "ontem"}}), encoding="utf-8")
    with pytest.raises(DataIntegrityError):
        _carrega(tmp_path)


def test_should_expose_the_date_in_the_serialized_entry(tmp_path: Path) -> None:
    _dados(tmp_path, [_termo("graca")])
    (tmp_path / "atualizacoes.json").write_text(json.dumps({"glossario": {"graca": "2026-09-20"}}), encoding="utf-8")

    entry = _carrega(tmp_path).get_by_slug(Category.GLOSSARIO, "graca")

    assert entry.model_dump(mode="json")["atualizado_em"] == "2026-09-20"


def test_should_have_a_date_for_almost_every_real_entry() -> None:
    """O manifesto commitado cobre o acervo real: sem isso o sitemap volta a ficar sem lastmod."""
    repo = Repository()
    repo.load()

    entradas = [e for cat in Category for e in repo.list_entries(cat, limit=10_000).itens]
    com_data = sum(1 for e in entradas if e.atualizado_em is not None)

    assert com_data / len(entradas) > 0.95
