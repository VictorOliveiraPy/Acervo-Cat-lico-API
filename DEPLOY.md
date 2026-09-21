# Deploy — backend no Render

> Preparado sem gastar token de API — é configuração de infraestrutura,
> não geração de código. Validado localmente (formato exato de env var,
> YAML) antes de escrever este guia.

Este é o repositório do **backend** (`Compendio-Catolico-API`). O frontend
mora no repositório irmão
[`Compendio-Catolico-Web`](https://github.com/VictorOliveiraPy/Compendio-Catolico-Web),
deploy no Vercel — ver `DEPLOY.md` de lá.

## Domínio de produção

O domínio `compendio-catolico.com` foi comprado no HostGator e a zona DNS
mora na Cloudflare (HostGator ficou só como registrador — nameservers
`ruth.ns.cloudflare.com` / `vin.ns.cloudflare.com`). O e-mail (Titan, via
HostGator) continua funcionando porque os registros `MX`/`SPF`/`DKIM` foram
preservados na Cloudflare tal como estavam.

- **Backend (este serviço)**: `api.compendio-catolico.com`, CNAME na
  Cloudflare apontando pro hostname `.onrender.com` do serviço no Render
  (custom domain configurado lá, certificado emitido automaticamente).
- **Frontend**: `compendio-catolico.com` (raiz) e `www.compendio-catolico.com`
  (redirect pra raiz), ambos no Vercel — ver `DEPLOY.md` do repositório do
  frontend.

Todo registro que aponta pra Render/Vercel fica como **DNS only** (nuvem
cinza) na Cloudflare — o proxy (nuvem laranja) pode atrapalhar a emissão do
certificado TLS desses provedores.

## Por que o backend vai primeiro

O backend precisa saber a origem do frontend (`CORS_ORIGINS`) e o
frontend precisa saber a URL do backend (`API_URL`) — uma
dependência circular. Resolvemos assim: **deploy do backend primeiro**
(a URL do Render é previsível e pode ficar provisoriamente com CORS
aberto só para desenvolvimento local), depois o frontend já sai
apontando pro backend certo, e por último voltamos aqui pra travar o
CORS na URL real do Vercel.

## 1. Deploy no Render

O repositório já tem `render.yaml` na raiz — o Render lê sozinho ao
conectar o repo.

1. No Render: **New > Blueprint**, aponte para este repositório
   (`Compendio-Catolico-API`).
2. O Render vai propor o serviço `acervo-catolico-api` (Python, build
   `pip install -r requirements.txt`, start
   `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, health check
   `/api/health`). Confirme a criação.
3. Antes de finalizar, preencha a variável `CORS_ORIGINS` (marcada
   `sync: false` no blueprint, ou seja, sem valor padrão) — por enquanto,
   deixe só a origem de desenvolvimento:
   ```
   ["http://localhost:3000"]
   ```
   **Formato importa**: é lista JSON, não string separada por vírgula —
   testado localmente, `pydantic-settings` rejeita CSV nesse campo.
4. Deploy. Quando terminar, anote a URL pública `.onrender.com` do
   serviço (aparece em Settings → o hostname exato depende do nome do
   serviço criado, confira ali antes de configurar DNS).
5. Confirme que subiu: `curl https://SUA-URL.onrender.com/api/health` —
   deve devolver `{"status":"ok","categorias":13,"total_entradas":485}`
   (ou mais, se o acervo tiver crescido).
6. Configure o domínio próprio: Settings → Custom Domains → adicione
   `api.compendio-catolico.com`. O Render mostra o CNAME de verificação —
   crie esse registro na Cloudflare (nome `api`, DNS only) e aguarde
   "Verified" + certificado emitido.

**Plano gratuito do Render "dorme" após inatividade** — a primeira
requisição depois de um tempo ocioso demora mais (cold start). Normal no
free tier; não é bug do backend.

## 2. Deploy do frontend

Feito no repositório irmão `Compendio-Catolico-Web` — root directory
`.` (é o próprio repo), variável `API_URL` apontando pra
URL do passo 1 com `/api` no final. Ver `DEPLOY.md` de lá.

## 3. Voltar aqui e travar o CORS

Com o domínio de produção do frontend em mãos:

1. No serviço do Render, edite a variável `CORS_ORIGINS` para a origem
   de produção de verdade:
   ```
   ["https://compendio-catolico.com","https://www.compendio-catolico.com"]
   ```
   Mantenha `http://localhost:3000` na lista só se ainda for testar
   contra o backend de produção a partir do seu ambiente local — senão,
   deixe só as duas origens do domínio.
2. Salve — o Render redeploya sozinho quando uma env var muda.
3. Confirme abrindo `https://compendio-catolico.com` e checando que a
   navegação/busca carrega dado de verdade (não erro de rede/CORS no
   console do navegador).

## Mural de velas (opcional)

O único recurso de escrita da API (`/api/velas`) guarda dado num Postgres à
parte — o Render free tem disco efêmero (apaga a cada deploy e às vezes ao
"acordar" de inatividade), então um SQLite local perderia o mural sozinho.

1. Crie uma conta grátis em [neon.tech](https://neon.tech) e um projeto novo
   (qualquer nome).
2. No painel do projeto, copie a **connection string** da branch padrão —
   algo como `postgresql://usuario:senha@ep-xxxx.aws.neon.tech/neondb?sslmode=require`.
3. No Render, Settings → Environment do serviço, adicione `DATABASE_URL`
   com essa string.
4. Redeploy (o Render faz sozinho ao salvar a env var). O lifespan cria a
   tabela `velas` sozinho na primeira subida (`CREATE TABLE IF NOT EXISTS`).
5. Confirme: `curl <backend>/api/velas` deve responder `200` com
   `{"total":0,...}` — antes de configurar `DATABASE_URL`, o mesmo endpoint
   responde `503`.

Sem `DATABASE_URL`, a API sobe normalmente e o resto do acervo funciona —
só `/api/velas` fica em 503 até a variável existir.

## Chatbot do acervo (opcional)

`/api/chat` (RAG — ver README, "Decisões que valem explicação") precisa do
mesmo Postgres do mural de velas, mais duas chaves de API pagas.

1. Chave da DeepSeek: crie em [platform.deepseek.com](https://platform.deepseek.com).
2. Chave da Voyage AI (embeddings): crie em [voyageai.com](https://www.voyageai.com) —
   o plano grátis cobre a indexação inicial dos 1.043 verbetes com sobra.
3. No Render, adicione `DEEPSEEK_API_KEY` e `VOYAGE_API_KEY` (Settings →
   Environment) — `DATABASE_URL` já deve existir (passo anterior).
4. Redeploy. O lifespan cria a tabela `rag_chunks` sozinho na primeira
   subida (`CREATE EXTENSION IF NOT EXISTS vector` + `CREATE TABLE IF NOT
   EXISTS`) — mas a tabela sobe **vazia**, sem chunk nenhum.
5. Popule o índice rodando o script localmente, apontando pro Postgres de
   produção (mesma `DATABASE_URL`, mesmas chaves, num `.env` local):
   ```bash
   python -m scripts.indexar_acervo
   ```
   Leva alguns minutos (1.043 verbetes, chamadas em lote à Voyage). Rodar de
   novo depois de editar `app/data/*.json` reindexa sem duplicar nada
   (`replace_source` apaga os chunks antigos do verbete antes de gravar).
6. Confirme: `curl -X POST <backend>/api/chat -H "Content-Type:
   application/json" -d '{"pergunta":"O que é a Crisma?"}'` deve responder
   `200` com uma resposta citando a fonte — antes de rodar o passo 5, a
   mesma pergunta responde com a recusa ("não encontrei isso no acervo"),
   porque o índice está vazio.

Sem as três variáveis (`DATABASE_URL`, `DEEPSEEK_API_KEY`,
`VOYAGE_API_KEY`), `/api/chat` responde `503` e o resto da API funciona
normalmente.

## Checklist antes de considerar o deploy "pronto"

- [ ] `curl <backend>/api/health` responde 200 com o total de entradas
      esperado.
- [ ] Site no Vercel carrega a home e pelo menos uma categoria sem erro
      no console.
- [ ] CORS do backend está travado na URL real do Vercel — **não** em
      `*` nem esquecido em `localhost`.
- [ ] `ENVIRONMENT=production` e `DEBUG=false` no Render — conferido
      automaticamente no boot (`app/core/config.py` recusa subir errado).
