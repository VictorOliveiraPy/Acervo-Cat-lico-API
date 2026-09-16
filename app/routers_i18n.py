"""Rotas HTTP das traduções do acervo — mesmo contrato de `app/routers.py`,
sob o prefixo `/api/i18n/{lang}/...`.

Prefixo `i18n` (não só `/api/{lang}/...`) de propósito: sem ele, o formato
de URL `/api/{lang}/{categoria}` (lista) seria idêntico a
`/api/{categoria}/{slug}` (detalhe de entrada em português) — os dois são
`/api/X/Y`. Com o segmento fixo `i18n` no meio, os dois formatos nunca
colidem, não importa a ordem em que os routers são registrados no app.

Rotas aditivas: não mudam nem substituem as rotas em português (sem
prefixo), que continuam sendo a fonte canônica servida por
`app.repository.repository`.
"""

from __future__ import annotations

from fastapi import APIRouter, Path, Query

from app.config import settings
from app.exceptions import LanguageNotFoundException
from app.i18n import translation_repositories
from app.models import AnyEntry, CategoryInfo, EntryPage, SearchResult
from app.repository import Repository

router = APIRouter(prefix="/api/i18n/{lang}", tags=["acervo (traduções)"])


def _resolve_repo(lang: str) -> Repository:
    """Repositório do idioma pedido, ou 404 se o idioma não é suportado."""
    repo = translation_repositories.get(lang)
    if repo is None:
        raise LanguageNotFoundException(lang)
    return repo


@router.get(
    "/categories",
    response_model=list[CategoryInfo],
    summary="Categorias já traduzidas para este idioma",
)
def list_categories(
    lang: str = Path(description="Código do idioma, ex.: 'es'."),
) -> list[CategoryInfo]:
    """Só as categorias já traduzidas — as demais ainda não têm URL aqui
    (tradução incremental, não é erro)."""
    return _resolve_repo(lang).list_categories()


@router.get(
    "/search",
    response_model=list[SearchResult],
    summary="Busca textual no acervo traduzido",
)
def search(
    lang: str = Path(description="Código do idioma, ex.: 'es'."),
    q: str = Query(
        min_length=2,
        max_length=100,
        description="Termo de busca (ignora caixa e acentos).",
    ),
    categoria: str | None = Query(
        default=None, description="Restringe a busca a uma categoria."
    ),
    limit: int = Query(default=settings.default_page_size, ge=1),
) -> list[SearchResult]:
    limit = min(limit, settings.max_search_results)
    return _resolve_repo(lang).search(q=q, categoria=categoria, limit=limit)


@router.get(
    "/{categoria}",
    response_model=EntryPage,
    summary="Lista entradas traduzidas de uma categoria (paginado)",
)
def list_entries(
    lang: str = Path(description="Código do idioma, ex.: 'es'."),
    categoria: str = Path(description="Slug da categoria, ex.: 'santos'."),
    limit: int = Query(default=settings.default_page_size, ge=1),
    offset: int = Query(default=0, ge=0),
) -> EntryPage:
    limit = min(limit, settings.max_page_size)
    return _resolve_repo(lang).list_entries(categoria=categoria, limit=limit, offset=offset)


@router.get(
    "/{categoria}/{slug}",
    response_model=AnyEntry,
    summary="Detalhe de uma entrada traduzida",
)
def get_entry(
    lang: str = Path(description="Código do idioma, ex.: 'es'."),
    categoria: str = Path(description="Slug da categoria, ex.: 'papas'."),
    slug: str = Path(description="Slug da entrada, ex.: 'joao-paulo-ii'."),
) -> AnyEntry:
    return _resolve_repo(lang).get_by_slug(categoria=categoria, slug=slug)
