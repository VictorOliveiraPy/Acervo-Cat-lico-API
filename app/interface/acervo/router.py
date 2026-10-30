"""Rotas HTTP do acervo — camada fina: valida entrada, chama o repositório, serializa.

Nenhuma regra de conteúdo mora aqui; ordenação, busca e 404 de domínio são
responsabilidade do `Repository`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Query

from app.core.config import settings
from app.infrastructure.acervo.json_repository import Repository, get_repository
from app.models import (
    AnyEntry,
    CategoryInfo,
    EntryPage,
    HealthStatus,
    SearchResult,
    ThemePage,
    ThemeSummary,
)

router = APIRouter(prefix="/api", tags=["acervo"])


@router.get("/health", response_model=HealthStatus, summary="Status da API")
def health(repo: Repository = Depends(get_repository)) -> HealthStatus:
    """Confirma que a API subiu **e** que o acervo está carregado em memória."""
    return HealthStatus(
        status="ok",
        categorias=len(repo.list_categories()),
        total_entradas=repo.total_entries,
    )


@router.get(
    "/categories",
    response_model=list[CategoryInfo],
    summary="Lista as categorias do acervo",
)
def list_categories(
    repo: Repository = Depends(get_repository),
) -> list[CategoryInfo]:
    """Categorias com nome, descrição, total de entradas e aviso editorial."""
    return repo.list_categories()


@router.get(
    "/search",
    response_model=list[SearchResult],
    summary="Busca textual no acervo",
)
def search(
    repo: Repository = Depends(get_repository),
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
    """Varre título, tags, resumo e corpo e devolve o trecho com o termo."""
    limit = min(limit, settings.max_search_results)
    return repo.search(q=q, categoria=categoria, limit=limit)


@router.get(
    "/temas",
    response_model=list[ThemeSummary],
    summary="Lista os temas do acervo",
)
def list_themes(
    min_total: int = Query(default=1, ge=1, description="Mínimo de entradas do tema."),
    repo: Repository = Depends(get_repository),
) -> list[ThemeSummary]:
    """Temas com o total de entradas. Declarada antes de `/{categoria}`, que a capturaria."""
    return repo.list_themes(min_total=min_total)


@router.get(
    "/temas/{slug}",
    response_model=ThemePage,
    summary="Entradas de um tema (paginado)",
)
def get_theme(
    slug: str = Path(description="Slug do tema, ex.: 'franciscanos'."),
    limit: int = Query(default=settings.default_page_size, ge=1),
    offset: int = Query(default=0, ge=0),
    repo: Repository = Depends(get_repository),
) -> ThemePage:
    """Entradas do tema, com as de cada categoria em sequência."""
    limit = min(limit, settings.max_page_size)
    return repo.get_theme(slug=slug, limit=limit, offset=offset)


@router.get(
    "/{categoria}",
    response_model=EntryPage,
    summary="Lista entradas de uma categoria (paginado)",
)
def list_entries(
    categoria: str = Path(description="Slug da categoria, ex.: 'santos'."),
    limit: int = Query(default=settings.default_page_size, ge=1),
    offset: int = Query(default=0, ge=0),
    repo: Repository = Depends(get_repository),
) -> EntryPage:
    """Página de entradas na ordem curada da categoria."""
    limit = min(limit, settings.max_page_size)
    return repo.list_entries(categoria=categoria, limit=limit, offset=offset)


@router.get(
    "/{categoria}/{slug}",
    response_model=AnyEntry,
    summary="Detalhe de uma entrada",
)
def get_entry(
    categoria: str = Path(description="Slug da categoria, ex.: 'papas'."),
    slug: str = Path(description="Slug da entrada, ex.: 'joao-paulo-ii'."),
    repo: Repository = Depends(get_repository),
) -> AnyEntry:
    """Entrada completa (corpo, campos próprios da categoria e fontes)."""
    return repo.get_by_slug(categoria=categoria, slug=slug)
