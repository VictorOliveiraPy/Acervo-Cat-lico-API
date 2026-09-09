"""Repositório em memória do acervo.

Todo o conteúdo cabe folgadamente na memória (poucos milhares de entradas no
pior caso), então a estratégia é: carregar e **validar** os JSONs uma única vez
no startup e servir tudo de estruturas prontas. Consequências assumidas:

* JSON inválido derruba o boot (`DataIntegrityError`) em vez de virar 500 em
  produção — falhar cedo é mais barato que falhar em runtime;
* a busca usa um índice pré-normalizado (sem acento, sem caixa) construído na
  carga, para não pagar `unicodedata` a cada requisição.
"""

from __future__ import annotations

import json
import logging
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from app.config import settings
from app.exceptions import (
    CategoryNotFoundException,
    DataIntegrityError,
    EntryNotFoundException,
)
from app.models import (
    AnyEntry,
    Category,
    CategoryInfo,
    Dataset,
    EntryPage,
    SearchResult,
)

logger = logging.getLogger(__name__)

DEFAULT_DATA_DIR = Path(__file__).parent / "data"

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
    """Acervo carregado em memória, com listagem, detalhe e busca."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self._data_dir = data_dir or settings.data_dir or DEFAULT_DATA_DIR
        self._datasets: dict[Category, Dataset] = {}
        self._entries: dict[Category, list[AnyEntry]] = {}
        self._by_slug: dict[Category, dict[str, AnyEntry]] = {}
        self._search_index: list[_SearchDoc] = []

    # ------------------------------------------------------------------ carga

    def load(self) -> None:
        """Carrega e valida todos os arquivos de dados.

        Monta as estruturas em variáveis locais e só então as publica: se um
        arquivo falhar, o repositório continua com o estado anterior em vez de
        ficar meio carregado.
        """
        datasets: dict[Category, Dataset] = {}
        entries: dict[Category, list[AnyEntry]] = {}
        by_slug: dict[Category, dict[str, AnyEntry]] = {}
        search_index: list[_SearchDoc] = []

        for category in Category:
            path = self._data_dir / f"{category.value}.json"
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

    @staticmethod
    def resolve_category(categoria: str | Category) -> Category:
        """Converte o segmento de URL em `Category` ou levanta 404."""
        if isinstance(categoria, Category):
            return categoria
        try:
            return Category(categoria)
        except ValueError as exc:
            raise CategoryNotFoundException(categoria) from exc

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
