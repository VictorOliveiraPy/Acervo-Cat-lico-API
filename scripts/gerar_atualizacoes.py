"""Gera `app/data/atualizacoes.json`: a data da última alteração de cada entrada.

A data vem do HISTÓRICO DO GIT, não da hora do arquivo (que muda a cada deploy): é a data do
commit em que o conteúdo da entrada nasceu ou mudou pela última vez. Entradas alteradas no
diretório de trabalho e ainda não commitadas ganham a data de hoje. Formatação do JSON que não
muda o conteúdo não conta como alteração.

O site usa esse dado como `lastmod` no sitemap; o Google só confia no campo quando ele é
verdadeiro, então uma data inventada seria pior que nenhuma.

    python scripts/gerar_atualizacoes.py                   # todas as categorias
    python scripts/gerar_atualizacoes.py --categoria santos papas
    python scripts/gerar_atualizacoes.py --check           # sai com 1 se o manifesto estiver desatualizado
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_REL = "app/data"
MANIFEST_NAME = "atualizacoes.json"

Versao = tuple[str, dict[str, dict]]  # (data ISO, slug -> item)


def assinatura(item: dict) -> str:
    """Hash do CONTEÚDO da entrada (ignora o próprio `atualizado_em` e a formatação)."""
    limpo = {k: v for k, v in item.items() if k != "atualizado_em"}
    return hashlib.sha1(  # noqa: S324 - só identifica conteúdo, não é segurança
        json.dumps(limpo, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def ultimas_alteracoes(versoes: list[Versao]) -> dict[str, str]:
    """`slug -> data` da última vez que a entrada nasceu ou mudou.

    `versoes` vem da mais antiga para a mais nova. Entradas que não existem mais na última
    versão são descartadas.
    """
    datas: dict[str, str] = {}
    anterior: dict[str, str] = {}
    for data, itens in versoes:
        atual = {slug: assinatura(item) for slug, item in itens.items()}
        for slug, sig in atual.items():
            if anterior.get(slug) != sig:
                datas[slug] = data
        anterior = atual
    ultimos = versoes[-1][1] if versoes else {}
    return {slug: data for slug, data in datas.items() if slug in ultimos}


def _git(root: Path, *args: str) -> str:
    return subprocess.run(  # noqa: S603
        ["git", "-C", str(root), *args],  # noqa: S607
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout


def _itens(texto: str) -> dict[str, dict]:
    bruto = json.loads(texto)
    return {i["slug"]: i for i in bruto.get("itens", []) if isinstance(i, dict) and "slug" in i}


def versoes_do_arquivo(root: Path, categoria: str, hoje: date) -> list[Versao]:
    """Versões commitadas do arquivo da categoria, da mais antiga à mais nova, mais o que está
    no diretório de trabalho (com a data de hoje) se for diferente do último commit."""
    rel = f"{DATA_REL}/{categoria}.json"
    versoes: list[Versao] = []
    linhas = _git(root, "log", "--reverse", "--format=%H%x09%cs", "--", rel).splitlines()
    for linha in linhas:
        sha, dia = linha.split("\t")
        try:
            versoes.append((dia, _itens(_git(root, "show", f"{sha}:{rel}"))))
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            continue  # commit que apagou ou quebrou o arquivo: não tem versão utilizável

    arquivo = root / rel
    if arquivo.exists():
        atual = _itens(arquivo.read_text(encoding="utf-8"))
        ultimo = versoes[-1][1] if versoes else {}
        if {s: assinatura(i) for s, i in atual.items()} != {s: assinatura(i) for s, i in ultimo.items()}:
            versoes.append((hoje.isoformat(), atual))
    return versoes


def gerar(root: Path, hoje: date, categorias: list[str] | None = None) -> dict[str, dict[str, str]]:
    """Manifesto completo (`categoria -> slug -> data`); `categorias` restringe o que recalcula."""
    data_dir = root / DATA_REL
    todas = sorted(
        p.stem
        for p in data_dir.glob("*.json")
        if p.name != MANIFEST_NAME and isinstance(json.loads(p.read_text(encoding="utf-8")), dict)
        and "_meta" in json.loads(p.read_text(encoding="utf-8"))
    )
    manifesto_atual = data_dir / MANIFEST_NAME
    resultado: dict[str, dict[str, str]] = (
        json.loads(manifesto_atual.read_text(encoding="utf-8")) if manifesto_atual.exists() else {}
    )
    for categoria in categorias or todas:
        resultado[categoria] = dict(sorted(ultimas_alteracoes(versoes_do_arquivo(root, categoria, hoje)).items()))
    return dict(sorted(resultado.items()))


def _serializar(manifesto: dict) -> str:
    return json.dumps(manifesto, ensure_ascii=False, indent=1, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--categoria", nargs="+", help="só estas categorias (nome do arquivo, sem .json)")
    parser.add_argument("--check", action="store_true", help="não grava; falha se estiver desatualizado")
    args = parser.parse_args()

    manifesto = gerar(ROOT, date.today(), args.categoria)
    destino = ROOT / DATA_REL / MANIFEST_NAME
    novo = _serializar(manifesto)

    if args.check:
        if not destino.exists() or destino.read_text(encoding="utf-8") != novo:
            print("atualizacoes.json desatualizado: rode python scripts/gerar_atualizacoes.py")
            return 1
        print("atualizacoes.json em dia")
        return 0

    destino.write_text(novo, encoding="utf-8")
    total = sum(len(v) for v in manifesto.values())
    print(f"{destino.relative_to(ROOT)}: {total} entradas em {len(manifesto)} categorias")
    return 0


if __name__ == "__main__":
    sys.exit(main())
