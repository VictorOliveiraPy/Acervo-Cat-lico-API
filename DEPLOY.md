# Deploy — backend no Render

> Preparado sem gastar token de API — é configuração de infraestrutura,
> não geração de código. Validado localmente (formato exato de env var,
> YAML) antes de escrever este guia.

Este é o repositório do **backend** (`Acervo-Cat-lico-API`). O frontend
mora no repositório irmão
[`Acervo-Cat-lico-Web`](https://github.com/VictorOliveiraPy/Acervo-Cat-lico-Web),
deploy no Vercel — ver `DEPLOY.md` de lá.

## Por que o backend vai primeiro

O backend precisa saber a origem do frontend (`CORS_ORIGINS`) e o
frontend precisa saber a URL do backend (`NEXT_PUBLIC_API_URL`) — uma
dependência circular. Resolvemos assim: **deploy do backend primeiro**
(a URL do Render é previsível e pode ficar provisoriamente com CORS
aberto só para desenvolvimento local), depois o frontend já sai
apontando pro backend certo, e por último voltamos aqui pra travar o
CORS na URL real do Vercel.

## 1. Deploy no Render

O repositório já tem `render.yaml` na raiz — o Render lê sozinho ao
conectar o repo.

1. No Render: **New > Blueprint**, aponte para este repositório
   (`Acervo-Cat-lico-API`).
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
4. Deploy. Quando terminar, anote a URL pública, algo como
   `https://acervo-catolico-api.onrender.com`.
5. Confirme que subiu: `curl https://SUA-URL.onrender.com/api/health` —
   deve devolver `{"status":"ok","categorias":10,"total_entradas":46}`
   (ou mais, se o acervo tiver crescido).

**Plano gratuito do Render "dorme" após inatividade** — a primeira
requisição depois de um tempo ocioso demora mais (cold start). Normal no
free tier; não é bug do backend.

## 2. Deploy do frontend

Feito no repositório irmão `Acervo-Cat-lico-Web` — root directory
`.` (é o próprio repo), variável `NEXT_PUBLIC_API_URL` apontando pra
URL do passo 1 com `/api` no final. Ver `DEPLOY.md` de lá.

## 3. Voltar aqui e travar o CORS

Com a URL real do Vercel em mãos:

1. No serviço do Render, edite a variável `CORS_ORIGINS` para a origem
   de produção de verdade:
   ```
   ["https://SUA-URL.vercel.app"]
   ```
   Mantenha `http://localhost:3000` na lista só se ainda for testar
   contra o backend de produção a partir do seu ambiente local — senão,
   deixe só a URL do Vercel.
2. Salve — o Render redeploya sozinho quando uma env var muda.
3. Confirme abrindo o site no Vercel e checando que a navegação/busca
   carrega dado de verdade (não erro de rede/CORS no console do
   navegador).

## Checklist antes de considerar o deploy "pronto"

- [ ] `curl <backend>/api/health` responde 200 com o total de entradas
      esperado.
- [ ] Site no Vercel carrega a home e pelo menos uma categoria sem erro
      no console.
- [ ] CORS do backend está travado na URL real do Vercel — **não** em
      `*` nem esquecido em `localhost`.
- [ ] `ENVIRONMENT=production` e `DEBUG=false` no Render — conferido
      automaticamente no boot (`app/config.py` recusa subir errado).
