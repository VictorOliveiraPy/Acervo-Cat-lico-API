# Layout do backend — Clean Architecture

Documento curto de orientação. A referência completa (camadas, regra de
dependência, fluxo de uma requisição, exemplos de imports permitidos/proibidos)
está em **[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)**; o passo a passo de
um endpoint novo está em **[`docs/ADDING_ENDPOINT.md`](docs/ADDING_ENDPOINT.md)**.

> Este arquivo substitui a versão antiga, que descrevia o layout achatado
> (`app/routers.py`, `app/repository.py`, `app/rag/`, etc.). **Aquele layout
> não existe mais.** Os nomes abaixo são os reais, conferíveis com
> `find app -type f -name "*.py"`.

## Estrutura real

```text
app/
├── main.py                  # entrypoint (app.main:app) — FastAPI, lifespan, CORS, routers
├── core/                    # cross-cutting
│   ├── config.py            #   Settings (pydantic-settings)
│   ├── exceptions.py        #   hierarquia base de exceções
│   └── rate_limiting.py     #   rate limiter
├── domain/                  # regras de negócio — Python puro, sem framework
│   ├── candles/{entities,repository}.py
│   ├── chat/{entities,repository,gateway,answer_generator,embedding_gateway,relevance,exceptions}.py
│   └── liturgy/{entities,repository,gateway,exceptions}.py
├── application/             # casos de uso
│   ├── candles/{light,list}_candle_use_case.py
│   ├── chat/{answer_question_use_case,chunking}.py
│   └── liturgy/get_daily_liturgy_use_case.py
├── infrastructure/          # implementações concretas dos contratos
│   ├── acervo/{json_repository,translations}.py
│   ├── candles/{postgres,in_memory}_repository.py
│   ├── chat/{postgres,in_memory}_repository.py + deepseek_answer_generator.py + voyage_embedding_gateway.py
│   └── liturgy/{http_gateway,in_memory,postgres}_repository.py
└── interface/               # adaptadores HTTP (única camada que conhece FastAPI)
    ├── exception_handlers.py
    ├── acervo/{router,i18n_router}.py
    ├── candles/{router,schemas}.py
    ├── chat/{router,schemas}.py
    └── liturgy/{router,schemas}.py
```

> **Divergência registrada:** o plano inicial citava `interfaces/`/`presentation/`
> e `domain/repositories/`. O repositório usa **`app/interface/`** e o contrato
> em **`app/domain/<dominio>/repository.py`** (arquivo, não pasta).

## Regra de dependência (resumo)

```text
interface → application → domain ← infrastructure
```

- `domain` e `application`: **sem** FastAPI, SQLAlchemy, asyncpg, httpx, Pydantic.
- `infrastructure`: implementa os contratos de `domain`.
- `interface`: única camada que importa FastAPI.
- Entrypoint: `app.main:app` (start command do Render: ver `render.yaml`).

Verificação automatizada: `python check_dep_rule.py .`

## Convenções de nome

- Arquivos e pacotes de módulo em **inglês** (`entities.py`, `repository.py`,
  `router.py`, `<verbo>_<substantivo>_use_case.py`).
- Campos de JSON que já são contrato de API ficam em **português** (`nome`,
  `intencao`, `criado_em`) — mudar quebra o frontend em produção.
- Docstrings e comentários em **português**.
