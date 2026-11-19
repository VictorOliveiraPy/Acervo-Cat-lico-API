"""Traduz o acervo para outros idiomas com o Claude, pelo Claude Code em modo não interativo.

Usa o comando `claude -p` da máquina (a assinatura do Claude Code), sem chave de
API. Cada verbete vira um pedido, e o `_meta` de cada categoria também. As
traduções saem em `app/data/i18n/<idioma>/<categoria>.json`, no mesmo formato
do português, e só são gravadas quando a categoria inteira volta válida.

    # Traduz as categorias que ainda não existem no idioma (pula as prontas):
    python -m scripts.traduzir_acervo --idiomas es en
    python -m scripts.traduzir_acervo --idiomas en --categorias sacramentos

    # Teste: só os 3 primeiros verbetes, gravados em .traducao/teste/ (fora do Git):
    python -m scripts.traduzir_acervo --idiomas en --categorias oracoes --limite 3

Pode parar e rodar de novo: cada verbete pronto fica guardado em `.traducao/pecas/`
até a categoria ser gravada, e não é traduzido outra vez. Se o limite de uso da
assinatura chegar, o script para; rode de novo depois.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.models import Dataset

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "app" / "data"
I18N = DADOS / "i18n"
TRABALHO = RAIZ / ".traducao"

MODELOS = {"sonnet": "claude-sonnet-5-5", "haiku": "claude-haiku-5-5"}
# Muda pela opção --modelo; o Haiku gasta bem menos do limite da assinatura.
MODELO = MODELOS["sonnet"]

IDIOMAS = {
    "es": {
        "nome": "Spanish",
        "exemplos": (
            "Pai Nosso → Padre Nuestro; Ave Maria → Dios te salve, María; "
            "São João Paulo II → San Juan Pablo II; Evangelho segundo Mateus 6,9-13 → "
            "Evangelio según Mateo 6,9-13; Catecismo da Igreja Católica → Catecismo de la Iglesia Católica"
        ),
    },
    "en": {
        "nome": "English",
        "exemplos": (
            "Pai Nosso → Our Father; Ave Maria → Hail Mary; São João Paulo II → "
            "Saint John Paul II; Evangelho segundo Mateus 6,9-13 → Gospel of Matthew 6:9-13; "
            "Catecismo da Igreja Católica → Catechism of the Catholic Church"
        ),
    },
}

# Campos que identificam o verbete: nunca mudam entre idiomas.
CAMPOS_FIXOS = {"id", "slug", "categoria", "status", "imagem"}


class LimiteDeUso(Exception):
    """A assinatura chegou ao limite: não adianta seguir mandando pedidos."""


def instrucoes(idioma: str) -> str:
    nome = IDIOMAS[idioma]["nome"]
    return f"""You translate entries of the Compêndio Católico, a Catholic reference website, from Brazilian Portuguese into {nome}.

You receive one JSON object. Reply with the same JSON object, every human-readable text value translated into {nome}, and nothing else: no comments, no code fences.

Rules:
- Keep every key, in the same order. Keep the values of `id`, `slug`, `categoria`, `status` and `imagem` exactly as they are, as well as every URL, number, date and null.
- Translate the strings inside lists too (tags, sources), keeping the number of items.
- Prayers, creeds, Bible verses and liturgical texts: use the official wording the Catholic Church uses in {nome}, never a literal translation. Bible references use the book names and the citation style customary in {nome}.
- Saints, popes, councils, documents and places take their established names in {nome}. Examples: {IDIOMAS[idioma]["exemplos"]}.
- Keep the meaning, the doctrinal precision, the tone, the line breaks and any Markdown. Do not add, remove, summarize or explain anything.
- Where the text talks about Brazil (customs, dioceses, feasts), translate it faithfully: do not adapt it to another country."""


def ler(caminho: Path) -> dict[str, Any]:
    return json.loads(caminho.read_text(encoding="utf-8"))


def categorias_em_portugues() -> list[str]:
    # Na mesma pasta há arquivos que não são categoria (o manifesto de imagens).
    return sorted(p.stem for p in DADOS.glob("*.json") if "_meta" in ler(p))


def sem_cercas(texto: str) -> str:
    texto = texto.strip()
    if texto.startswith("```"):
        texto = texto.split("\n", 1)[1].rsplit("```", 1)[0]
    return texto


def conferir(original: Any, traduzido: Any, caminho: str = "") -> list[str]:
    """Diferenças de forma: chaves, tamanho das listas e valores que não podiam mudar."""
    if isinstance(original, dict):
        if not isinstance(traduzido, dict) or list(original) != list(traduzido):
            return [f"{caminho or 'raiz'}: chaves diferentes"]
        erros: list[str] = []
        for chave, valor in original.items():
            if chave in CAMPOS_FIXOS and traduzido[chave] != valor:
                erros.append(f"{caminho}{chave}: mudou")
            else:
                erros += conferir(valor, traduzido[chave], f"{caminho}{chave}.")
        return erros
    if isinstance(original, list):
        if not isinstance(traduzido, list) or len(original) != len(traduzido):
            return [f"{caminho}: lista com outro tamanho"]
        return [
            e
            for o, t in zip(original, traduzido, strict=True)
            for e in conferir(o, t, caminho)
        ]
    if isinstance(original, str):
        if not isinstance(traduzido, str):
            return [f"{caminho}: deixou de ser texto"]
        # Fonte que começa com link pode ter descrição depois; só o link é intocável.
        if original.startswith(("http://", "https://")) and (
            traduzido.split()[:1] != original.split()[:1]
        ):
            return [f"{caminho}: URL mudou"]
        return []
    return [] if original == traduzido else [f"{caminho}: valor mudou"]


def perguntar_ao_claude(idioma: str, objeto: dict[str, Any]) -> str:
    """Uma tradução pelo `claude -p`, sem ferramentas e sem guardar a sessão."""
    claude = shutil.which("claude")
    if claude is None:
        raise SystemExit(
            "O comando `claude` (Claude Code) não está instalado nesta máquina."
        )
    # Argumentos fixos; o texto do verbete vai pela entrada padrão, nunca pela linha de comando.
    processo = subprocess.run(  # noqa: S603
        [
            claude,
            "-p",
            "--model",
            MODELO,
            "--tools",
            "",
            "--effort",
            "low",
            "--no-session-persistence",
            "--output-format",
            "json",
            "--system-prompt",
            instrucoes(idioma),
        ],
        input=json.dumps(objeto, ensure_ascii=False, indent=2),
        capture_output=True,
        text=True,
        # Fora do repositório: assim o CLAUDE.md do projeto não entra no pedido.
        cwd=tempfile.gettempdir(),
        timeout=900,
    )
    try:
        saida = json.loads(processo.stdout)
    except json.JSONDecodeError as erro:
        texto = (processo.stdout + processo.stderr).strip()
        if "limit" in texto.lower():
            raise LimiteDeUso(texto[:200]) from erro
        raise RuntimeError(f"saída inesperada do claude: {texto[:200]}") from erro
    if saida.get("is_error"):
        texto = str(saida.get("result", ""))
        if "limit" in texto.lower():
            raise LimiteDeUso(texto[:200])
        raise RuntimeError(texto[:200])
    return str(saida["result"])


def traduzir_peca(
    idioma: str, original: dict[str, Any], guardada: Path
) -> dict[str, Any]:
    """Traduz um verbete (ou o `_meta`), tenta mais uma vez se vier fora do formato."""
    if guardada.exists():
        return ler(guardada)
    problema = ""
    for _ in range(2):
        try:
            traduzido = json.loads(sem_cercas(perguntar_ao_claude(idioma, original)))
        except json.JSONDecodeError:
            problema = "resposta não é JSON"
            continue
        erros = conferir(original, traduzido)
        if not erros:
            guardada.parent.mkdir(parents=True, exist_ok=True)
            guardada.write_text(
                json.dumps(traduzido, ensure_ascii=False), encoding="utf-8"
            )
            return traduzido
        problema = "; ".join(erros[:3])
    raise ValueError(problema)


def traduzir_categoria(
    idioma: str, categoria: str, destino: Path, limite: int | None, paralelo: int
) -> list[str]:
    dados = ler(DADOS / f"{categoria}.json")
    itens = dados["itens"][:limite] if limite else dados["itens"]
    partes: list[tuple[str, dict[str, Any]]] = [("_meta", dados["_meta"])] + [
        (str(i), item) for i, item in enumerate(itens)
    ]
    pecas = TRABALHO / "pecas" / idioma / categoria

    def uma(parte: tuple[str, dict[str, Any]]) -> tuple[str, dict[str, Any] | str]:
        nome, original = parte
        try:
            return nome, traduzir_peca(idioma, original, pecas / f"{nome}.json")
        except (ValueError, RuntimeError, subprocess.TimeoutExpired) as erro:
            return nome, f"{idioma}/{categoria}#{nome}: {erro}"

    with ThreadPoolExecutor(max_workers=paralelo) as executor:
        resultados = dict(executor.map(uma, partes))

    falhas = [r for r in resultados.values() if isinstance(r, str)]
    if falhas:
        return falhas
    arquivo = {
        "_meta": resultados["_meta"],
        "itens": [resultados[str(i)] for i in range(len(itens))],
    }
    try:
        Dataset.model_validate(arquivo)
    except ValidationError as erro:
        return [
            f"{idioma}/{categoria}: não passa no modelo ({erro.error_count()} erros)"
        ]
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(arquivo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for peca in pecas.glob("*.json"):
        peca.unlink()
    return []


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--idiomas", nargs="+", choices=sorted(IDIOMAS), required=True)
    parser.add_argument("--categorias", nargs="+", choices=categorias_em_portugues())
    parser.add_argument(
        "--limite",
        type=int,
        help="só os N primeiros verbetes, gravados em .traducao/teste/",
    )
    parser.add_argument(
        "--refazer", action="store_true", help="traduz de novo mesmo se já existir"
    )
    parser.add_argument(
        "--paralelo", type=int, default=4, help="pedidos ao mesmo tempo (padrão 4)"
    )
    parser.add_argument(
        "--modelo", choices=sorted(MODELOS), default="sonnet", help="padrão: sonnet"
    )
    args = parser.parse_args()
    global MODELO
    MODELO = MODELOS[args.modelo]

    pasta = TRABALHO / "teste" if args.limite else I18N
    falhas: list[str] = []
    try:
        for idioma in args.idiomas:
            for categoria in args.categorias or categorias_em_portugues():
                destino = pasta / idioma / f"{categoria}.json"
                if destino.exists() and not args.refazer:
                    continue
                print(f"{idioma}/{categoria}…", flush=True)
                problemas = traduzir_categoria(
                    idioma, categoria, destino, args.limite, args.paralelo
                )
                falhas += problemas
                print(
                    f"  {'gravada' if not problemas else f'{len(problemas)} problemas'}",
                    flush=True,
                )
    except LimiteDeUso as erro:
        print(
            f"Parou: limite de uso da assinatura ({erro}). Rode de novo mais tarde; o que ficou pronto não se perde."
        )
        sys.exit(2)

    if falhas:
        print(f"{len(falhas)} problemas (rode de novo para tentar só esses):")
        for falha in falhas:
            print(f"  - {falha}")
        sys.exit(1)
    print("Pronto.")


if __name__ == "__main__":
    main()
