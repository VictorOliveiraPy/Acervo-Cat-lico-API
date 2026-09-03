# Acervo Católico — Backend (FastAPI)

API somente-leitura que serve conteúdo católico curado em 8 categorias:
**santos, papas, concílios, milagres eucarísticos, doutores da Igreja,
catecismo, crisma e história**.

> **Nota sobre a arquitetura:** o repositório não contém `docs/ARCHITECTURE.md`.
> Este backend foi implementado a partir da especificação funcional acordada
> (modelos, dados, repositório, rotas) e as decisões de contrato estão
> documentadas aqui e nas docstrings dos módulos.

---

## Como executar

Requer Python 3.11+.

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

- API: <http://localhost:8000/api/health>
- Docs interativas (Swagger): <http://localhost:8000/docs>
- CORS liberado para `http://localhost:3000` e `http://127.0.0.1:3000`
  (somente `GET`/`OPTIONS`, sem credenciais).

## Comandos de desenvolvimento

```bash
pytest -q --cov            # testes + cobertura (fail_under = 70)
ruff check app tests       # lint
mypy app                   # tipagem
```

---

## Endpoints

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/health` | Status da API e total de entradas carregadas |
| GET | `/api/categories` | Categorias com nome, descrição, `total` e aviso editorial |
| GET | `/api/search?q=&categoria=&limit=` | Busca textual (mín. 2 caracteres) |
| GET | `/api/{categoria}?limit=&offset=` | Listagem paginada de uma categoria |
| GET | `/api/{categoria}/{slug}` | Detalhe de uma entrada |

### Exemplos

```bash
curl "http://localhost:8000/api/categories"
curl "http://localhost:8000/api/santos?limit=2&offset=0"
curl "http://localhost:8000/api/papas/joao-paulo-ii"
curl "http://localhost:8000/api/search?q=oracao&limit=5"
curl "http://localhost:8000/api/search?q=teresa&categoria=doutores-igreja"
```

### Formatos de resposta

Listagem (`EntryPage`):

```json
{ "categoria": "santos", "total": 3, "limit": 2, "offset": 0, "itens": [ ... ] }
```

Busca (`SearchResult[]`) — apenas o necessário para a lista de resultados:

```json
[{ "categoria": "santos", "slug": "teresa-de-avila",
   "titulo": "Santa Teresa de Ávila", "trecho": "…mestra da oração…" }]
```

Erro (contrato estável para o frontend — a `message` é UX e pode mudar,
o `code` **não** muda sem aviso):

```json
{ "code": "ENTRY_NOT_FOUND", "message": "Nenhuma entrada 'x' na categoria 'santos'.",
  "details": { "categoria": "santos", "slug": "x" } }
```

Códigos usados: `CATEGORY_NOT_FOUND` (404), `ENTRY_NOT_FOUND` (404),
`INTERNAL_ERROR` (500). Erro de parâmetro (ex.: `q` com 1 caractere) usa o
`422` padrão do FastAPI.

---

## Estrutura

```
.
├── app/
│   ├── config.py       # Settings (pydantic-settings), CORS, limites de página
│   ├── exceptions.py   # exceções de domínio + handlers HTTP
│   ├── models.py       # Pydantic v2: ContentEntry + 8 subclasses, união discriminada
│   ├── repository.py   # carga/validação no startup, listagem, detalhe e busca
│   ├── routers.py      # rotas finas /api/*
│   ├── main.py         # app, lifespan, CORS, handlers
│   └── data/*.json     # conteúdo curado, um arquivo por categoria
└── tests/
    ├── test_repository.py  # unitários (sem HTTP)
    └── test_routers.py     # integração via TestClient
```

> Este repositório é o irmão de
> [`Acervo-Cat-lico-Web`](https://github.com/VictorOliveiraPy/Acervo-Cat-lico-Web)
> (frontend Next.js) — mesma convenção usada em `melhorperfil-api`/`melhorperfil-web`
> e `santo-guardiao-api`/`santo-guardiao-web`. Deploy: ver `DEPLOY.md`.

### Decisões que valem explicação

- **Sem banco de dados.** O acervo é pequeno e somente-leitura: os 8 JSONs são
  carregados e **validados** no `lifespan`. JSON malformado, campo desconhecido
  (`extra="forbid"`) ou slug duplicado levantam `DataIntegrityError` e a
  aplicação **não sobe** — melhor falhar no boot que responder 500 em produção.
- **União discriminada por `categoria`.** Cada subclasse fixa
  `categoria: Literal[...]`, então o detalhe de um papa serializa
  `numero_ordem` e o de um santo serializa `festa`/`patronato`, sem campo
  genérico do tipo `extras`.
- **Datas como texto onde a história é imprecisa.** `nascimento`, `morte`,
  `pontificado_*` e `ano` (milagres) são `str | None` para permitir
  `"c. 1181-1182"` ou `"século VIII (segundo a tradição local)"`. Onde a data é
  certa e numérica (`ano_inicio`/`ano_fim` de concílios,
  `ano_proclamacao` de doutores) o campo é `int`.
- **Busca insensível a caixa e acento com trecho de contexto.** A normalização
  é feita caractere a caractere e **preserva o comprimento** da string; é isso
  que permite localizar o termo no texto normalizado e recortar o trecho no
  texto original sem manter um mapa de índices. Campos são varridos por ordem
  de relevância (título → tags → resumo → corpo); quando o casamento ocorre em
  campo curto (título/tag), o `trecho` mostra o resumo, que tem contexto útil.
- **Ordenação curada.** Categorias com `ordem`/`numero_ordem` (catecismo,
  crisma, papas, concílios) saem nessa sequência; as demais preservam a ordem
  do arquivo JSON, que é editorial — não alfabética.
- **404 para categoria desconhecida.** `/api/xpto` responde
  `404 CATEGORY_NOT_FOUND` (URL inexistente) em vez do `422` que sairia se a
  categoria fosse validada como enum no path.

---

## Regra editorial do conteúdo (`app/data/*.json`)

O conteúdo atual é um **conjunto inicial de exemplos**, não um catálogo
definitivo. Isso está declarado no próprio dado: cada arquivo tem um bloco
`_meta` com `status: "exemplos-iniciais"`, `aviso` e `revisao_editorial`, e o
`aviso` é devolvido pelo endpoint `/api/categories` para que a interface possa
exibi-lo.

Ao adicionar entradas, siga as mesmas regras que valem para o que já está lá:

1. **Nada inventado.** Se não há certeza documental, o campo é omitido
   (`null`), não estimado.
2. **Imprecisão declarada.** Datas tradicionais ou aproximadas aparecem como
   `"c. 1181-1182"`, `"século XIII (segundo a tradição local)"` — nunca
   convertidas em número exato para "ficar bonito".
3. **`fontes` é obrigatório na prática.** Cada entrada cita referências
   verificáveis: Catecismo da Igreja Católica (com número de parágrafo),
   documentos conciliares, atos pontifícios, Escritura.
4. **Só o universalmente reconhecido.** Casos controversos ou de devoção não
   aprovada ficam fora; milagres eucarísticos entram apenas com culto e
   documentação eclesiástica reconhecidos, e o texto lembra que são devoção
   aprovada, não artigo de fé.
5. **Revisão eclesiástica.** Para uso catequético real, o material deve ser
   revisado por autoridade competente — a API não substitui isso.

Conteúdo atual: 25 entradas (3 por categoria; 4 no catecismo, uma por parte do
CIC).

## Configuração

Todas as variáveis são opcionais em desenvolvimento (há defaults em
`app/config.py`) e podem ir num `.env` na raiz do repositório:

| Variável | Default | Descrição |
|---|---|---|
| `ENVIRONMENT` | `development` | Em `production`, o boot falha se `DEBUG=true` ou se `CORS_ORIGINS` tiver `*` |
| `DEBUG` | `true` | Nível de log |
| `CORS_ORIGINS` | `["http://localhost:3000","http://127.0.0.1:3000"]` | Origens permitidas |
| `DATA_DIR` | `app/data` | Diretório alternativo de conteúdo |
| `DEFAULT_PAGE_SIZE` / `MAX_PAGE_SIZE` | `20` / `100` | Paginação |
| `MAX_SEARCH_RESULTS` | `50` | Teto de resultados da busca |
