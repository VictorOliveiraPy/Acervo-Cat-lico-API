"""Repositórios de tradução do acervo (idiomas além do português).

O português é o canônico, servido por `app.repository.repository` nas rotas
sem prefixo de idioma (`/api/<categoria>`) — este módulo não muda nem
substitui isso. Cada idioma traduzido vive em `app/data/i18n/<lang>/`,
espelhando a mesma estrutura de `app/data/` (um arquivo por categoria, mesmo
schema Pydantic), carregado por um `Repository(strict=False)` próprio:
tradução é incremental por natureza, então é normal a pasta ter só algumas
das 49 categorias por enquanto — a categoria ainda não traduzida
simplesmente não existe nesse idioma (404), em vez de derrubar o boot.
"""

from __future__ import annotations

from app.repository import DEFAULT_DATA_DIR, Repository

# Adicionar um idioma novo aqui só depois de `app/data/i18n/<lang>/` existir
# no repositório com pelo menos um arquivo de categoria — a ordem aqui é a
# ordem de prioridade de tradução (ver planejamento de i18n do site).
SUPPORTED_LANGUAGES: tuple[str, ...] = ("es",)

I18N_DATA_DIR = DEFAULT_DATA_DIR / "i18n"

translation_repositories: dict[str, Repository] = {
    lang: Repository(data_dir=I18N_DATA_DIR / lang, strict=False)
    for lang in SUPPORTED_LANGUAGES
}


def load_translations() -> None:
    """Carrega todos os repositórios de tradução — chamado no lifespan,
    ao lado de `repository.load()` (o português)."""
    for repo in translation_repositories.values():
        repo.load()
