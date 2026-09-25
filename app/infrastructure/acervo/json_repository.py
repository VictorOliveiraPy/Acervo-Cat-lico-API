"""Repositório em memória do acervo.

Todo o conteúdo cabe folgadamente na memória (poucos milhares de entradas no
pior caso), então a estratégia é: carregar e **validar** os JSONs uma única vez
no startup e servir tudo de estruturas prontas. Consequências assumidas:

* JSON inválido derruba o boot (`DataIntegrityError`) em vez de virar 500 em
  produção — falhar cedo é mais barato que falhar em runtime;
* a busca usa um índice pré-normalizado (sem acento, sem caixa) construído na
  carga, para não pagar `unicodedata` a cada requisição.

Sem `domain/acervo/repository.py` (uma interface abstrata) de propósito,
diferente de velas/liturgia/chat: aqui existe uma única implementação real
(sempre foi, e não há Postgres nem fake alternativo à vista), então uma
interface só documentaria um contrato que nunca tem uma segunda classe do
outro lado — ver `standards/backend.md` no repositório `dev-agent`, seção
"DRY over ceremony". `app/models.py` (entidades) também fica fora do padrão
`domain/`/`interface` por decisão explícita: aqui não há transformação
entre o dado de domínio e o schema de resposta HTTP (é uma API só de
leitura, sem lógica própria) — duplicar a classe seria ritual, não proteção.
"""

from __future__ import annotations

import json
import logging
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from app.core.config import settings
from app.core.exceptions import (
    CategoryNotFoundException,
    DataIntegrityError,
    EntryNotFoundException,
)
from app.image_assets import ImageAssetResolver
from app.models import (
    AnyEntry,
    Category,
    CategoryInfo,
    Dataset,
    EntryPage,
    SearchResult,
)

logger = logging.getLogger(__name__)

# Manifesto de datas de atualização, ao lado dos arquivos de dados (ver scripts/gerar_atualizacoes.py).
UPDATES_FILENAME = "atualizacoes.json"

# `app/infrastructure/acervo/json_repository.py` -> sobe três níveis pra
# chegar em `app/`, onde `data/` mora — movido de `app/repository.py`
# (Clean Architecture, 2026-09-19), dois níveis de diretório a mais do que
# antes (mesma pegadinha já corrigida em `app/core/config.py` na Fase 1).
DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data"

# Prioridade de relevância dos campos varridos pela busca (menor = melhor).
_FIELD_TITULO = 0
_FIELD_TAGS = 1
_FIELD_RESUMO = 2
_FIELD_CORPO = 3

_EXCERPT_WINDOW = 90
_SUMMARY_EXCERPT_LIMIT = 220


def _normalize_char(char: str) -> str:
    """Normaliza um caractere preservando o comprimento (1 char → 1 char).

    O comprimento é preservado de propósito: é isso que permite usar o índice
    encontrado no texto normalizado para recortar o trecho no texto original,
    sem manter um mapa de posições em paralelo.
    """
    decomposed = unicodedata.normalize("NFKD", char)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    folded = stripped.casefold()
    if not folded:
        return char
    return folded[0]


def normalize(text: str) -> str:
    """Devolve o texto sem acentos e em caixa baixa, com o mesmo comprimento."""
    return "".join(_normalize_char(char) for char in text)


def build_excerpt(
    text: str,
    normalized: str,
    start: int,
    length: int,
    window: int = _EXCERPT_WINDOW,
) -> str:
    """Recorta o trecho do texto original em torno da ocorrência do termo.

    `normalized` é a versão normalizada de `text` (mesmo comprimento), e
    `start`/`length` localizam o termo nela. Elipses indicam corte.
    """
    end = start + length
    left = max(0, start - window)
    right = min(len(text), end + window)

    # Evita cortar palavra ao meio nas bordas do recorte.
    if left > 0:
        space = text.find(" ", left, start)
        if space != -1:
            left = space + 1
    if right < len(text):
        space = text.rfind(" ", end, right)
        if space != -1:
            right = space

    snippet = " ".join(text[left:right].split())
    prefix = "…" if left > 0 else ""
    suffix = "…" if right < len(text) else ""
    return f"{prefix}{snippet}{suffix}"


def _summary_excerpt(resumo: str) -> str:
    """Trecho de fallback quando o termo casou em título ou tag (textos curtos)."""
    clean = " ".join(resumo.split())
    if len(clean) <= _SUMMARY_EXCERPT_LIMIT:
        return clean
    return clean[:_SUMMARY_EXCERPT_LIMIT].rstrip() + "…"


@dataclass(frozen=True)
class _IndexedField:
    """Campo de uma entrada já normalizado para busca."""

    priority: int
    original: str
    normalized: str


@dataclass(frozen=True)
class _SearchDoc:
    """Documento do índice de busca (uma entrada do acervo)."""

    categoria: Category
    slug: str
    titulo: str
    resumo: str
    fields: tuple[_IndexedField, ...]


def _sort_key(indexed: tuple[int, AnyEntry]) -> tuple[int, int, int]:
    """Ordena por ordem explícita (`ordem`/`numero_ordem`) e, sem ela, pela
    ordem curada no arquivo JSON — que é editorial, não alfabética."""
    position, entry = indexed
    explicit = getattr(entry, "ordem", None)
    if explicit is None:
        explicit = getattr(entry, "numero_ordem", None)
    if explicit is None:
        return (1, 0, position)
    return (0, explicit, position)


class Repository:
    """Acervo carregado em memória, com listagem, detalhe e busca.

    `strict=True` (padrão, usado pelo idioma canônico — português) exige um
    arquivo por categoria do enum `Category`: lacuna aí é erro de integridade
    dos dados, não estado válido. `strict=False` é o modo usado pelos
    repositórios de tradução (`app/data/i18n/<lang>/`): a tradução é
    incremental por natureza — a categoria cujo arquivo ainda não existe é
    simplesmente omitida (a API responde 404 pra ela nesse idioma), em vez de
    derrubar o boot inteiro por uma categoria que ainda não foi traduzida.
    """

    def __init__(self, data_dir: Path | None = None, *, strict: bool = True) -> None:
        self._data_dir = data_dir or settings.data_dir or DEFAULT_DATA_DIR
        self._strict = strict
        self._datasets: dict[Category, Dataset] = {}
        self._entries: dict[Category, list[AnyEntry]] = {}
        self._by_slug: dict[Category, dict[str, AnyEntry]] = {}
        self._search_index: list[_SearchDoc] = []
        self._updates: dict[str, dict[str, str]] = {}

    # ------------------------------------------------------------------ carga

    def _load_updates(self) -> dict[str, dict[str, str]]:
        """Manifesto `atualizacoes.json` (`categoria -> slug -> data`); ausente = sem datas."""
        path = self._data_dir / UPDATES_FILENAME
        if not path.exists():
            return {}
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise DataIntegrityError(f"{path.name}: JSON inválido — {exc}") from exc
        if not isinstance(raw, dict):
            raise DataIntegrityError(f"{path.name}: esperado um objeto categoria -> slug -> data.")
        return raw

    def load(self) -> None:
        """Carrega e valida os arquivos de dados disponíveis.

        Monta as estruturas em variáveis locais e só então as publica: se um
        arquivo falhar, o repositório continua com o estado anterior em vez de
        ficar meio carregado.
        """
        datasets: dict[Category, Dataset] = {}
        entries: dict[Category, list[AnyEntry]] = {}
        by_slug: dict[Category, dict[str, AnyEntry]] = {}
        search_index: list[_SearchDoc] = []
        self._updates = self._load_updates()
        image_resolver = ImageAssetResolver(
            settings.image_manifest_path, settings.image_cdn_base_url
        )

        for category in Category:
            path = self._data_dir / f"{category.value}.json"
            if not self._strict and not path.exists():
                continue
            dataset = self._load_dataset(category, path)

            ordered = [
                entry
                for _, entry in sorted(enumerate(dataset.itens), key=_sort_key)
            ]
            index: dict[str, AnyEntry] = {}
            for entry in ordered:
                if entry.slug in index:
                    raise DataIntegrityError(
                        f"{path.name}: slug duplicado '{entry.slug}'."
                    )
                entry.imagem = image_resolver.resolve(entry.imagem)
                index[entry.slug] = entry
                search_index.append(self._index_entry(entry))

            datasets[category] = dataset
            entries[category] = ordered
            by_slug[category] = index

        self._datasets = datasets
        self._entries = entries
        self._by_slug = by_slug
        self._search_index = search_index

        logger.info(
            "Acervo carregado",
            extra={
                "categorias": len(datasets),
                "total_entradas": self.total_entries,
                "data_dir": str(self._data_dir),
            },
        )

    def _load_dataset(self, category: Category, path: Path) -> Dataset:
        """Lê um arquivo de categoria, convertendo qualquer falha em erro claro."""
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise DataIntegrityError(
                f"{path.name}: arquivo de dados ausente para a categoria "
                f"'{category.value}'."
            ) from exc
        except json.JSONDecodeError as exc:
            raise DataIntegrityError(f"{path.name}: JSON inválido — {exc}") from exc

        # Injeta a data de atualização do manifesto (quando a entrada não traz a sua).
        dates = self._updates.get(category.value, {})
        if isinstance(raw, dict):
            for item in raw.get("itens", []):
                if isinstance(item, dict) and "atualizado_em" not in item:
                    date_value = dates.get(item.get("slug", ""))
                    if date_value:
                        item["atualizado_em"] = date_value

        try:
            dataset = Dataset.model_validate(raw)
        except ValidationError as exc:
            raise DataIntegrityError(
                f"{path.name}: conteúdo não passou na validação — {exc}"
            ) from exc

        if dataset.meta.categoria != category:
            raise DataIntegrityError(
                f"{path.name}: metadados declaram categoria "
                f"'{dataset.meta.categoria.value}', esperado '{category.value}'."
            )
        for entry in dataset.itens:
            if entry.categoria != category:
                raise DataIntegrityError(
                    f"{path.name}: entrada '{entry.slug}' declara categoria "
                    f"'{entry.categoria.value}'."
                )
        return dataset

    @staticmethod
    def _index_entry(entry: AnyEntry) -> _SearchDoc:
        """Pré-normaliza título, tags, resumo e corpo de uma entrada."""
        raw_fields = [
            (_FIELD_TITULO, entry.titulo),
            (_FIELD_TAGS, ", ".join(entry.tags)),
            (_FIELD_RESUMO, entry.resumo),
            (_FIELD_CORPO, entry.corpo),
        ]
        fields = tuple(
            _IndexedField(priority=priority, original=text, normalized=normalize(text))
            for priority, text in raw_fields
            if text
        )
        return _SearchDoc(
            categoria=entry.categoria,
            slug=entry.slug,
            titulo=entry.titulo,
            resumo=entry.resumo,
            fields=fields,
        )

    # ------------------------------------------------------------------ leitura

    @property
    def total_entries(self) -> int:
        """Total de entradas carregadas em todas as categorias."""
        return sum(len(items) for items in self._entries.values())

    def all_entries(self) -> list[AnyEntry]:
        """Todas as entradas de todas as categorias, na ordem curada de cada uma.

        Existe para quem precisa varrer o acervo inteiro (hoje: o script de
        indexação do chatbot, `scripts/indexar_acervo.py`) sem depender de
        `_entries` — atributo privado por design, pra não virar contrato
        implícito de mais um consumidor além do `load()`.
        """
        return [entry for items in self._entries.values() for entry in items]

    def resolve_category(self, categoria: str | Category) -> Category:
        """Converte o segmento de URL em `Category` carregada neste
        repositório, ou levanta 404.

        Não é `@staticmethod` de propósito: um repositório de tradução
        (`strict=False`) pode ter uma `Category` válida no enum mas ainda sem
        arquivo carregado (categoria não traduzida ainda nesse idioma) — o
        segmento de URL é válido, mas não existe *neste* acervo, o mesmo 404
        de uma categoria que não existe em lugar nenhum.
        """
        try:
            category = categoria if isinstance(categoria, Category) else Category(categoria)
        except ValueError as exc:
            raise CategoryNotFoundException(str(categoria)) from exc
        if category not in self._datasets:
            raise CategoryNotFoundException(category.value)
        return category

    def list_categories(self) -> list[CategoryInfo]:
        """Lista as categorias com total de entradas e aviso editorial."""
        return [
            CategoryInfo(
                categoria=category,
                nome=dataset.meta.nome,
                descricao=dataset.meta.descricao,
                total=len(self._entries[category]),
                aviso=dataset.meta.aviso,
            )
            for category, dataset in self._datasets.items()
        ]

    def list_entries(
        self,
        categoria: str | Category,
        limit: int = 20,
        offset: int = 0,
    ) -> EntryPage:
        """Página de entradas de uma categoria, na ordem curada."""
        category = self.resolve_category(categoria)
        items = self._entries[category]
        limit = max(limit, 0)
        offset = max(offset, 0)
        return EntryPage(
            categoria=category,
            total=len(items),
            limit=limit,
            offset=offset,
            itens=items[offset : offset + limit],
        )

    def get_by_slug(self, categoria: str | Category, slug: str) -> AnyEntry:
        """Entrada única por categoria + slug; 404 se não existir."""
        category = self.resolve_category(categoria)
        entry = self._by_slug[category].get(slug)
        if entry is None:
            raise EntryNotFoundException(category.value, slug)
        return entry

    def search(
        self,
        q: str,
        categoria: str | Category | None = None,
        limit: int = 20,
    ) -> list[SearchResult]:
        """Busca textual insensível a caixa e acento em título, tags, resumo e corpo.

        O `trecho` traz o contexto ao redor do termo; quando o casamento ocorre
        em campo curto (título ou tag), o contexto útil é o resumo.
        """
        term = normalize(q).strip()
        if not term:
            return []

        category = self.resolve_category(categoria) if categoria else None
        matches: list[tuple[int, int, SearchResult]] = []

        for position, doc in enumerate(self._search_index):
            if category is not None and doc.categoria != category:
                continue
            best = self._best_match(doc, term)
            if best is None:
                continue
            priority, trecho = best
            matches.append(
                (
                    priority,
                    position,
                    SearchResult(
                        categoria=doc.categoria,
                        slug=doc.slug,
                        titulo=doc.titulo,
                        trecho=trecho,
                    ),
                )
            )

        matches.sort(key=lambda item: (item[0], item[1]))
        return [result for _, _, result in matches[: max(limit, 0)]]

    @staticmethod
    def _best_match(doc: _SearchDoc, term: str) -> tuple[int, str] | None:
        """Melhor campo casado (menor prioridade) e o trecho correspondente."""
        for field in doc.fields:
            start = field.normalized.find(term)
            if start == -1:
                continue
            if field.priority in (_FIELD_TITULO, _FIELD_TAGS):
                return field.priority, _summary_excerpt(doc.resumo)
            return field.priority, build_excerpt(
                field.original, field.normalized, start, len(term)
            )
        return None


# Instância única usada pela aplicação; o lifespan do `main` chama `load()`.
repository = Repository()


def get_repository() -> Repository:
    """Dependência do FastAPI — permite `dependency_overrides` em testes."""
    return repository
