# Compêndio Católico — Backend (FastAPI)

API somente-leitura que serve conteúdo católico curado em 13 categorias:
**santos, papas, concílios, milagres eucarísticos, doutores da Igreja,
catecismo, crisma, história, Nossa Senhora, livros, orações, pecados e
vida litúrgica**.

> **Arquitetura:** Clean Architecture por domínio (domain / application /
> infrastructure / interface). Camadas, regra de dependência e fluxo de uma
> requisição estão em [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md); como
> adicionar um endpoint novo, em
> [`docs/ADDING_ENDPOINT.md`](docs/ADDING_ENDPOINT.md).

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

Clean Architecture por domínio (ver [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)):

```
.
├── app/
│   ├── main.py                  # app, lifespan (acervo + pool do mural), CORS, routers
│   ├── core/                    # config.py (Settings), exceptions.py, rate_limiting.py
│   ├── domain/                  # regras de negócio — Python puro, sem framework
│   │   ├── candles/             # entities.py, repository.py (contrato)
│   │   ├── chat/                # entities, repository, gateways, relevance, exceptions
│   │   └── liturgy/             # entities, repository, gateway, exceptions
│   ├── application/             # casos de uso (orquestram entidade + contrato)
│   │   ├── candles/             # light_candle_use_case.py, list_candles_use_case.py
│   │   ├── chat/                # answer_question_use_case.py, chunking.py
│   │   └── liturgy/             # get_daily_liturgy_use_case.py
│   ├── infrastructure/          # implementações concretas dos contratos
│   │   ├── acervo/              # json_repository.py, translations.py
│   │   ├── candles/             # postgres_repository.py, in_memory_repository.py
│   │   ├── chat/                # postgres/in_memory repos, deepseek_*, llm_client, voyage_*
│   │   └── liturgy/             # http_gateway.py, postgres/in_memory repos
│   └── interface/               # adaptadores HTTP (única camada que conhece FastAPI)
│       ├── exception_handlers.py
│       ├── acervo/              # router.py, i18n_router.py
│       ├── candles/             # router.py, schemas.py
│       ├── chat/                # router.py, schemas.py
│       └── liturgy/             # router.py, schemas.py
├── scripts/
│   ├── indexar_acervo.py        # popula/reindexa o índice do chatbot — `python -m scripts.indexar_acervo`
│   └── sincronizar_imagens.py   # sincroniza assets de imagem pro CDN
└── tests/
    ├── domain/                  # entidades, sem I/O
    ├── application/             # um caso de uso por vez, com repositório fake
    ├── infrastructure/          # repositório real contra banco de teste
    └── interface/               # TestClient ponta a ponta (wiring)
```

> O **entrypoint real** é `app.main:app` (é o que o `render.yaml` e o
> `DEPLOY.md` usam como start command).

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
  indexado por `scripts/indexar_acervo.py`); o DeepSeek só vê os trechos
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

### Datas de atualização (`atualizado_em`)

Cada entrada devolve `atualizado_em` (`AAAA-MM-DD`): a data em que o conteúdo dela nasceu ou mudou pela última vez.
O site a usa como `lastmod` no sitemap, e o Google só confia nesse campo quando ele é verdadeiro. A data **não** está
nos arquivos de conteúdo: vem de `app/data/atualizacoes.json`, gerado do histórico do git por
`scripts/gerar_atualizacoes.py` (`make atualizacoes`) e injetado na carga. Formatação do JSON que não muda o
conteúdo não conta como alteração, e entradas editadas e ainda não commitadas ganham a data de hoje.

**Depois de alterar qualquer entrada, rode `make atualizacoes` e commite o manifesto junto.**
`python scripts/gerar_atualizacoes.py --check` confere se ele está em dia.

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
| `DEEPSEEK_API_KEY` | *(nenhum)* | Chave da DeepSeek — sem ela, `/api/chat` responde `503` |
| `VOYAGE_API_KEY` | *(nenhum)* | Chave da Voyage AI (embeddings) — sem ela, `/api/chat` responde `503` |
| `DEEPSEEK_MODEL` | `deepseek-chat` | Modelo da DeepSeek que gera a resposta do chat |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | Endpoint da DeepSeek (API compatível com OpenAI) |
| `VOYAGE_EMBEDDING_MODEL` / `VOYAGE_EMBEDDING_DIMENSIONS` | `voyage-3.5-lite` / `512` | Mudam juntos — a dimensão é fixa na coluna `vector(N)` do Postgres; trocar o modelo sem migrar a coluna quebra a indexação. Trocar o modelo (mesmo mantendo a dimensão) exige rodar `python -m scripts.indexar_acervo` de novo — vetores antigos não são comparáveis com os do modelo novo |
| `CHAT_MAX_CONTEXT_CHUNKS` | `6` | Quantos trechos do acervo entram no prompt de cada pergunta |
