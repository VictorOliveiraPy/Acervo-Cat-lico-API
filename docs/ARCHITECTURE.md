# Arquitetura do backend

Clean Architecture (Uncle Bob) por domínio. Quatro camadas com
responsabilidades fixas; a **regra de dependência não é opcional**:
dependências apontam só para dentro.

```text
interface  →  application  →  domain
                                     ↑
infrastructure ──────────────────────┘
```

`domain` e `application` são **Python puro**: nunca importam FastAPI,
Pydantic, asyncpg, httpx nem nada de framework. `infrastructure` é a única
camada que importa driver (asyncpg, httpx, openai, voyageai) e implementa
os contratos de `domain`. `interface` é a única camada que conhece FastAPI.

## Camadas reais (nomes conferidos no repositório)

| Camada | Caminho real | Responsabilidade |
|---|---|---|
| Domínio — entidades | `app/domain/<dominio>/entities.py` | Entidades/value objects (`dataclass`, `Enum`). Sem Pydantic, sem ORM, sem I/O. |
| Domínio — contratos | `app/domain/<dominio>/repository.py` | Contrato de acesso a dados (`ABC`). Só a interface, nunca a implementação. |
| Domínio — gateways | `app/domain/<dominio>/gateway.py` | Contrato de serviço externo (ex.: fonte da liturgia diária). |
| Domínio — exceções | `app/domain/<dominio>/exceptions.py` e `app/core/exceptions.py` | Exceções tipadas (`AppException` e filhas). |
| Aplicação | `app/application/<dominio>/<verbo>_<substantivo>_use_case.py` | Caso de uso: orquestra entidades + o contrato do repositório. |
| Infraestrutura | `app/infrastructure/<dominio>/` | Implementações concretas: `postgres_repository.py`, `in_memory_repository.py`, `http_gateway.py`, `deepseek_answer_generator.py`, `voyage_embedding_gateway.py`. |
| Interface | `app/interface/<dominio>/router.py` e `schemas.py` | Camada mais fina: parseia requisição → chama **um** caso de uso → serializa resposta. Sem regra de negócio, sem SQL. |
| Núcleo / cross-cutting | `app/core/` (`config.py`, `exceptions.py`, `rate_limiting.py`) | Configuração, hierarquia base de exceções, rate limiting. |
| Composição (entrypoint) | `app/main.py` | Cria o `FastAPI`, monta o `lifespan`, middleware CORS, registra handlers e faz `include_router`. |

> **Divergência de nome face ao plano inicial:** o plano citava
> `domain/repositories/` e `interfaces|presentation/`. No repositório real os
> diretórios são **`app/domain/<dominio>/repository.py`** (arquivo único, não
> pasta `repositories/`) e **`app/interface/`** (não `interfaces/` nem
> `presentation/`). A doc segue os nomes que existem.

## Fluxo de uma requisição HTTP

Exemplo real: `POST /api/velas` (acender uma vela).

```text
1. interface   app/interface/candles/router.py
                 └─ valida o corpo com CandleCreateRequest (Pydantic)
                 └─ rate limit + resolve o repositório via Depends
2. application app/application/candles/light_candle_use_case.py
                 └─ orquestra: recebe a entidade NewCandle, chama o contrato
3. domain      app/domain/candles/repository.py  (contrato CandleRepository)
                 └─ app/domain/candles/entities.py (Candle/NewCandle/CandleType)
4. infrastructure app/infrastructure/candles/postgres_repository.py
                 └─ implementa o contrato sobre asyncpg (SQL real mora aqui)
5. interface   (de volta) serializa Candle → CandleResponse → JSON 201
```

A rota não conhece SQL; o caso de uso não conhece HTTP; o domínio não conhece
nem HTTP nem banco.

## Regra de dependência — imports permitidos e proibidos

**Permitido** (apontam para dentro):

```python
# application → domain  (OK)
from app.domain.candles.repository import CandleRepository
from app.domain.candles.entities import Candle

# interface → application + domain  (OK)
from app.application.candles.list_candles_use_case import ListCandlesUseCase
from app.domain.candles.repository import CandleRepository

# infrastructure → domain  (OK — implementa o contrato)
from app.domain.candles.repository import CandleRepository
```

**Proibido** (violam a regra de dependência):

```python
# ❌ domain importando framework — domain é Python puro
from fastapi import HTTPException
from pydantic import BaseModel
import asyncpg

# ❌ application importando framework — use case não sabe o que é HTTP
from fastapi import Depends
from sqlalchemy.orm import Session

# ❌ interface acessando o repositório direto (tem que passar pelo use case)
from app.infrastructure.candles.postgres_repository import PostgresCandleRepository
```

Verificação automática (usada no gate de CI):

```bash
python check_dep_rule.py .     # varre app/domain e app/application por imports de framework
ruff check app tests
mypy app
pytest -q
```

## Três classes, três papéis

Entidade, modelo ORM e schema de API **são classes diferentes** — mudar um não
força mudar o outro:

| Papel | Exemplo real | Onde |
|---|---|---|
| Entidade | `Candle` (dataclass) | `app/domain/candles/entities.py` |
| Schema HTTP (DTO) | `CandleCreateRequest` / `CandleResponse` | `app/interface/candles/schemas.py` |
| Mapeamento de banco | `_candle_from_row` + SQL em `PostgresCandleRepository` | `app/infrastructure/candles/postgres_repository.py` |

## Erros

Exceções tipadas em `app/core/exceptions.py` carregam `status_code` + `code`
(string estável = contrato com o frontend) + `details`. Quem converte em
resposta HTTP é `app/interface/exception_handlers.py`. Casos de uso e domínio
**levantam exceção de domínio, nunca `HTTPException`** (HTTP é conceito de
interface).

## Ver também

- Como adicionar um endpoint novo: [`ADDING_ENDPOINT.md`](ADDING_ENDPOINT.md).
- Layout resumido e decisões: [`../new_layout.md`](../new_layout.md).
- Deploy/entrypoint: [`../DEPLOY.md`](../DEPLOY.md).
