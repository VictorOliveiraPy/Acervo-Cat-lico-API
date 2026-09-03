"""Configuração única da aplicação (pydantic-settings, lida uma só vez).

Regra do time: nada de `os.getenv` espalhado. Tudo passa por `Settings`, e
invariantes de segurança que só valem em produção falham no boot — é melhor
não subir do que subir com CORS aberto para qualquer origem.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuração da API do acervo."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "Acervo Católico API"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = True

    # O frontend de desenvolvimento roda em localhost:3000 (Next/CRA).
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Permite apontar para outro diretório de conteúdo (usado em testes).
    data_dir: Path | None = None

    # Teto de itens por página, para uma requisição não puxar o acervo inteiro.
    max_page_size: int = 100
    default_page_size: int = 20
    max_search_results: int = 50

    @field_validator("*", mode="before")
    @classmethod
    def empty_string_to_none(cls, value: Any) -> Any:
        """Trata variável de ambiente vazia como ausente (`FOO=` → None)."""
        if isinstance(value, str) and value.strip() == "":
            return None
        return value

    @property
    def is_production(self) -> bool:
        """Verdadeiro quando o ambiente é produção."""
        return self.environment.lower() in {"production", "prod"}

    @model_validator(mode="after")
    def enforce_production_invariants(self) -> Settings:
        """Falha no boot se a configuração de produção estiver insegura."""
        if self.is_production:
            if self.debug:
                raise ValueError("DEBUG não pode estar ativo em produção.")
            if "*" in self.cors_origins:
                raise ValueError(
                    "CORS_ORIGINS não pode conter curinga '*' em produção."
                )
        return self


@lru_cache
def get_settings() -> Settings:
    """Devolve a instância única de Settings (lida uma vez por processo)."""
    return Settings()


settings = get_settings()
