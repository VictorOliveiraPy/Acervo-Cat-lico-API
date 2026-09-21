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

# `app/core/config.py` -> sobe dois níveis pra chegar em `app/`, onde
# `data/` mora — movido de `app/config.py` (Clean Architecture, 2026-09-19),
# um nível de diretório a mais do que antes.
_APP_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Configuração da API do acervo."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "Compêndio Católico API"
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

    # Imagens são sincronizadas antes do deploy. Enquanto a URL do CDN não é
    # configurada, a API preserva a URL editorial original — rollout seguro.
    image_manifest_path: Path = _APP_DIR / "data" / "image-manifest.json"
    image_cdn_base_url: str | None = None

    # String de conexão Postgres para o mural de velas (feature opcional):
    # sem ela, os endpoints de /api/velas respondem 503 em vez de derrubar
    # a API inteira — o acervo de leitura não pode depender de um banco à
    # parte. Formato: postgresql://usuario:senha@host/banco?sslmode=require
    database_url: str | None = None

    # Chatbot do acervo (RAG, `/api/chat`) — feature opcional como o mural de
    # velas: sem as duas chaves de API abaixo (ou sem `DATABASE_URL`, que
    # guarda os embeddings), o endpoint responde 503 em vez de derrubar a
    # API inteira. `voyage_embedding_model`/`_dimensions` têm que mudar
    # juntos — a dimensão do vetor é fixa na coluna do Postgres
    # (`CREATE TABLE ... vector(N)`), trocar o modelo sem migrar a coluna
    # quebra a indexação.
    #
    # `voyage-3-lite` foi APOSENTADO pela Voyage (incidente real de produção:
    # /api/chat respondendo 503, `InvalidRequestError: Model voyage-3-lite is
    # not supported`) — sucessor é `voyage-3.5-lite`, que ainda aceita
    # `output_dimension=512` (matryoshka embedding, ver
    # voyage_embedding_gateway.py), então a dimensão não precisa mudar. O que
    # MUDA de verdade: os vetores já indexados foram gerados pelo modelo
    # antigo — buscar com o modelo novo contra eles dá similaridade sem
    # sentido (espaços vetoriais diferentes, mesmo com a mesma dimensão
    # numérica). É obrigatório rodar `python -m scripts.indexar_acervo` de
    # novo em produção depois de trocar o modelo, senão o chat volta a
    # funcionar mas com busca degradada silenciosamente.
    #
    # LLM (geração da resposta): DeepSeek via SDK `openai` (API compatível) —
    # `DEEPSEEK_API_KEY` é a chave, `DEEPSEEK_MODEL` o modelo (default
    # `deepseek-chat`) e `DEEPSEEK_BASE_URL` o endpoint (default
    # `https://api.deepseek.com`). Ver `app/infrastructure/chat/llm_client.py`.
    deepseek_api_key: str | None = None
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    voyage_api_key: str | None = None
    voyage_embedding_model: str = "voyage-3.5-lite"
    voyage_embedding_dimensions: int = 512
    chat_max_context_chunks: int = 6

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
