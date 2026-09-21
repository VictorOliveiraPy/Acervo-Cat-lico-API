# Como adicionar um endpoint

Passo a passo do caminho completo, do contrato ao registro do router. Siga a
ordem: cada passo depende do anterior (a regra de dependência anda de dentro
para fora).

> **Não se cria mais nada em `app/api/routes`.** Esse layout antigo **não
> existe** neste repositório. Router novo vai em
> `app/interface/<dominio>/router.py`. Confirmar sempre com:
> `find app -type f -name "*.py"` antes de assumir um caminho.

Exemplo abaixo: um recurso hipotético `intencoes` dentro do domínio `candles`.
Troque pelos nomes reais do seu domínio.

---

## 1. Entidade (domínio) — `app/domain/<dominio>/entities.py`

Python puro. **Sem Pydantic, sem ORM, sem I/O.**

```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class Intention:
    """Intenção de oração já validada, pronta pra persistir."""
    id: int
    text: str
```

## 2. Contrato do repositório (domínio) — `app/domain/<dominio>/repository.py`

Só a interface (`ABC`), nunca a implementação:

```python
from abc import ABC, abstractmethod

class IntentionRepository(ABC):
    """Contrato que os casos de uso dependem."""

    @abstractmethod
    async def list_all(self) -> list[Intention]: ...
```

## 3. Caso de uso (aplicação) — `app/application/<dominio>/<verbo>_<substantivo>_use_case.py`

Orquestra entidade + contrato. Depois de pronto, o use case **não** pode
importar FastAPI, SQL ou Pydantic.

```python
class ListIntentionsUseCase:
    """Lista as intenções de oração cadastradas."""

    def __init__(self, repository: IntentionRepository) -> None:
        self._repository = repository

    async def execute(self) -> list[Intention]:
        return await self._repository.list_all()
```

## 4. Implementação (infraestrutura) — `app/infrastructure/<dominio>/`

Aqui — e só aqui — mora SQL/driver. As duas implementações que o projeto usa:

```python
# app/infrastructure/candles/postgres_repository.py
class PostgresIntentionRepository(IntentionRepository):
    def __init__(self, pool: AsyncPool) -> None:
        self._pool = pool

    async def list_all(self) -> list[Intention]:
        rows = await self._pool.fetch("SELECT id, text FROM intencoes")
        return [Intention(id=r["id"], text=r["text"]) for r in rows]
```

```python
# app/infrastructure/candles/in_memory_repository.py  (usado nos testes)
class InMemoryIntentionRepository(IntentionRepository):
    def __init__(self) -> None:
        self._items: list[Intention] = []

    async def list_all(self) -> list[Intention]:
        return list(self._items)
```

## 5. Schemas HTTP (interface) — `app/interface/<dominio>/schemas.py`

DTOs Pydantic. **Diferentes** da entidade e do modelo de banco.

> **Cuidado com o contrato publicado:** nomes de CAMPO em JSON (ex.: `nome`,
> `intencao`) estão em português de propósito — são o que o frontend já
> consome em produção. Mudar aqui quebra o contrato. Só nomes de
> classe/método são ingleses.

```python
class IntentionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    texto: str

    @classmethod
    def from_entity(cls, intention: Intention) -> "IntentionResponse":
        return cls(id=intention.id, texto=intention.text)
```

## 6. Router (interface) — `app/interface/<dominio>/router.py`

Fino: parseia → chama **um** caso de uso → serializa. Sem regra de negócio,
sem SQL, sem acessar repositório direto (vai pelo use case).

```python
router = APIRouter(prefix="/api/intencoes", tags=["intencoes"])

@router.get("", response_model=list[IntentionResponse])
async def list_intentions(
    repo: IntentionRepository = Depends(get_intention_repository),
) -> list[IntentionResponse]:
    """Lista as intenções públicas."""
    items = await ListIntentionsUseCase(repo).execute()
    return [IntentionResponse.from_entity(i) for i in items]
```

## 7. Registrar o router — `app/main.py`

```python
from app.interface.intencoes.router import router as intentions_router

# Cuidado com a ordem: rotas específicas ANTES da rota coringa
# `/api/{categoria}` do acervo, senão `/api/intencoes` vira slug de
# categoria inexistente.
app.include_router(intentions_router)
app.include_router(router)  # router do acervo por último
```

## 8. Testar (obrigatório antes de declarar pronto)

Testes por camada, com as camadas de baixo falsificadas:

```text
tests/application/<dominio>/   → use case + repositório fake (dict em memória)
tests/interface/<dominio>/     → TestClient real (assinatura/serialização)
tests/domain/<dominio>/        → entidades, sem I/O
```

Nomes no padrão `test_should_{what}_when_{cause}`, corpo em Given/When/Then.

## 9. Validar (gate)

```bash
python check_dep_rule.py .   # nenhuma violação de camada
ruff check app tests
mypy app
pytest -q --cov
```

Um teste vermelho é tarefa bloqueada, não nota de rodapé.

---

### Resumo do caminho

```text
entity → protocol → use case → implementation → controller/router → registrar
domain/  domain/    application/ infrastructure/  interface/         main.py
```
