# Compêndio Católico — Backend (FastAPI)

API somente-leitura que serve conteúdo católico curado em 13 categorias:
**santos, papas, concílios, milagres eucarísticos, doutores da Igreja,
catecismo, crisma, história, Nossa Senhora, livros, orações, pecados e
vida litúrgica**.

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
| GET | `/api/velas?limit=&offset=` | Mural de velas acesas (mais recentes primeiro) |
| POST | `/api/velas` | Acende uma vela (`nome`, `intencao?`, `tipo`) — única rota de escrita |
| GET | `/api/liturgia-diaria?data=` | Liturgia do dia: cor, celebração e leituras da Missa (padrão: hoje, horário de Brasília) |
| POST | `/api/chat` | Pergunta ao chatbot do acervo (RAG) — `{"pergunta": "..."}` → resposta + fontes citadas |

### Exemplos

```bash
curl "http://localhost:8000/api/categories"
curl "http://localhost:8000/api/santos?limit=2&offset=0"
curl "http://localhost:8000/api/papas/joao-paulo-ii"
curl "http://localhost:8000/api/search?q=oracao&limit=5"
curl "http://localhost:8000/api/search?q=teresa&categoria=doutores-igreja"
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"pergunta": "O que é a Crisma?"}'
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

Chatbot (`ChatResponse`) — `fontes` vem vazia quando nada no acervo bateu
com a pergunta (nesse caso `resposta` é a recusa, não uma tentativa de
responder mesmo assim: ver "Decisões que valem explicação" abaixo):

```json
{ "resposta": "A Crisma é o sacramento que...",
  "fontes": [{ "titulo": "Crisma", "categoria": "crisma", "slug": "o-sacramento-da-confirmacao" }] }
```

Erro (contrato estável para o frontend — a `message` é UX e pode mudar,
o `code` **não** muda sem aviso):

```json
{ "code": "ENTRY_NOT_FOUND", "message": "Nenhuma entrada 'x' na categoria 'santos'.",
  "details": { "categoria": "santos", "slug": "x" } }
```

Códigos usados: `CATEGORY_NOT_FOUND` (404), `ENTRY_NOT_FOUND` (404),
`VELAS_INDISPONIVEL` (503, sem `DATABASE_URL` configurada),
`RATE_LIMITED` (429, uma vela por IP a cada ~20s no mural; ~6s por IP no chat),
`LITURGIA_INDISPONIVEL` (503, sem `DATABASE_URL` ou fonte externa fora do ar),
`CHAT_INDISPONIVEL` (503, sem `DATABASE_URL`/`ANTHROPIC_API_KEY`/`VOYAGE_API_KEY`
configuradas, ou falha ao chamar alguma das duas APIs),
`INTERNAL_ERROR` (500).
Erro de parâmetro (ex.: `q` com 1 caractere) usa o `422` padrão do FastAPI.

---

## Estrutura

```
.
├── app/
│   ├── config.py          # Settings (pydantic-settings), CORS, limites de página
│   ├── exceptions.py      # exceções de domínio + handlers HTTP
│   ├── models.py          # Pydantic v2: ContentEntry + subclasses, união discriminada
│   ├── repository.py      # carga/validação no startup, listagem, detalhe e busca
│   ├── routers.py         # rotas finas /api/* do acervo (somente leitura)
│   ├── velas_models.py    # Pydantic do mural de velas (a única escrita da API)
│   ├── velas_repository.py# Postgres (produção) e in-memory (testes), mesma interface
│   ├── velas_router.py    # rotas /api/velas (GET público, POST com rate limit)
│   ├── liturgia_models.py     # Pydantic da liturgia diária (leituras da Missa)
│   ├── liturgia_client.py     # busca e parseia a fonte externa (função pura, sem I/O)
│   ├── liturgia_repository.py # cache em Postgres (1 busca/dia) e in-memory (testes)
│   ├── liturgia_router.py     # rota /api/liturgia-diaria
│   ├── rag/                   # chatbot do acervo (RAG) — fase 1: só o acervo, sem PDF
│   │   ├── chunking.py         # quebra verbete em pedaços indexáveis (função pura)
│   │   ├── embeddings.py       # cliente Voyage AI (embedding de documento e de consulta)
│   │   ├── repository.py       # índice em Postgres/pgvector, e em memória (testes)
│   │   ├── generation.py       # prompt + chamada ao Claude, com o guard-rail central
│   │   └── models.py           # contrato HTTP (ChatRequest/ChatResponse) e ChunkResult
│   ├── chat_router.py     # rota /api/chat (rate limit próprio, mais folgado que o mural)
│   ├── main.py            # app, lifespan (acervo + pool do mural), CORS, handlers
│   └── data/*.json        # conteúdo curado, um arquivo por categoria
├── scripts/
│   └── indexar_acervo.py  # popula/reindexa app/rag — `python -m scripts.indexar_acervo`
└── tests/
    ├── test_repository.py     # unitários (sem HTTP)
    ├── test_routers.py        # integração via TestClient (acervo)
    ├── test_velas.py          # integração do mural (repositório em memória)
    ├── test_liturgia.py       # parsing + integração da liturgia diária (fetcher fake)
    ├── test_rag_chunking.py   # chunking, com verbetes reais do acervo
    ├── test_rag_generation.py # guard-rail contra alucinação, isolado (sem rede)
    └── test_chat.py           # integração do chatbot (Voyage/Claude sempre mockados)
```

> Este repositório é o irmão de
> [`Compendio-Catolico-Web`](https://github.com/VictorOliveiraPy/Compendio-Catolico-Web)
> (frontend Next.js) — mesma convenção usada em `melhorperfil-api`/`melhorperfil-web`
> e `santo-guardiao-api`/`santo-guardiao-web`. Deploy: ver `DEPLOY.md`.

### Decisões que valem explicação

- **Acervo sem banco de dados; mural de velas com um, à parte.** O acervo é
  somente-leitura: os JSONs são carregados e **validados** no `lifespan`. JSON
  malformado, campo desconhecido (`extra="forbid"`) ou slug duplicado
  levantam `DataIntegrityError` e a aplicação **não sobe** — melhor falhar no
  boot que responder 500 em produção. Já o mural de velas (`/api/velas`) é a
  única escrita persistida da API, e por isso guarda em Postgres (`DATABASE_URL`,
  opcional — ver `DEPLOY.md`, "Mural de velas"); sem essa variável, o acervo
  sobe normalmente e só `/api/velas` responde `503`.
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
- **Liturgia diária cacheada, nunca buscada em tempo real por requisição.**
  A fonte (`api-liturgia-diaria.vercel.app`, agregador de terceiros — não é
  um serviço oficial da CNBB nem do Vaticano; não encontramos uma API pública
  oficial em português) é buscada no máximo uma vez por dia e o resultado
  fica gravado em Postgres; todas as requisições seguintes daquele dia leem
  do cache. Isso isola o site da lentidão/instabilidade de um serviço de
  terceiros de graça. Reusa o mesmo `DATABASE_URL` do mural de velas — sem
  ele, `/api/liturgia-diaria` responde `503`, igual ao mural.
- **Chatbot nunca responde do que o modelo "sabe" — só do acervo (RAG).**
  Toda pergunta busca primeiro nos embeddings do próprio conteúdo
  (`app/domain/chat/`, `app/application/chat/` e `app/infrastructure/chat/`,
  indexado por `scripts/indexar_acervo.py`); o Claude só vê os trechos
  recuperados e é instruído a recusar em vez de completar com conhecimento
  próprio. Abaixo de `SIMILARITY_THRESHOLD`
  (`app/domain/chat/relevance.py`), nem chama a API — devolve a recusa
  direto, sem gastar uma chamada paga que já se sabe que não tem como
  responder bem.
  Fase 1 (atual): só os 1.043 verbetes do acervo. Livros em PDF ficam para
  uma fase seguinte, com um script de ingestão próprio.

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

Conteúdo atual: 485 entradas nas 13 categorias.

## Configuração

Todas as variáveis são opcionais em desenvolvimento (há defaults em
`app/core/config.py`) e podem ir num `.env` na raiz do repositório:

| Variável | Default | Descrição |
|---|---|---|
| `ENVIRONMENT` | `development` | Em `production`, o boot falha se `DEBUG=true` ou se `CORS_ORIGINS` tiver `*` |
| `DEBUG` | `true` | Nível de log |
| `CORS_ORIGINS` | `["http://localhost:3000","http://127.0.0.1:3000"]` | Origens permitidas |
| `DATA_DIR` | `app/data` | Diretório alternativo de conteúdo |
| `DEFAULT_PAGE_SIZE` / `MAX_PAGE_SIZE` | `20` / `100` | Paginação |
| `MAX_SEARCH_RESULTS` | `50` | Teto de resultados da busca |
| `DATABASE_URL` | *(nenhum)* | Postgres do mural de velas, do cache da liturgia diária e do índice do chatbot — sem ela, `/api/velas`, `/api/liturgia-diaria` e `/api/chat` respondem `503` e o resto da API funciona normalmente |
| `ANTHROPIC_API_KEY` | *(nenhum)* | Chave da Anthropic — sem ela, `/api/chat` responde `503` |
| `VOYAGE_API_KEY` | *(nenhum)* | Chave da Voyage AI (embeddings) — sem ela, `/api/chat` responde `503` |
| `CHAT_MODEL` | `claude-sonnet-5` | Modelo do Claude que gera a resposta do chat |
| `VOYAGE_EMBEDDING_MODEL` / `VOYAGE_EMBEDDING_DIMENSIONS` | `voyage-3-lite` / `512` | Mudam juntos — a dimensão é fixa na coluna `vector(N)` do Postgres; trocar o modelo sem migrar a coluna quebra a indexação |
| `CHAT_MAX_CONTEXT_CHUNKS` | `6` | Quantos trechos do acervo entram no prompt de cada pergunta |
