# Tarefa 4 — Operação e publicação

**Status:** concluída

## Objetivo

Documentar a execução segura para que o primeiro acesso do usuário nunca faça download da Wikimedia.

## Requisitos

- Rodar a sincronização antes do deploy da API e do frontend.
- Publicar `app/static/img-acervo/` em bucket/CDN com cache longo e imutável.
- Configurar `IMAGE_CDN_BASE_URL` somente depois que os assets e o manifesto estiverem publicados.
- Interromper a publicação quando houver falhas de download não aprovadas pela curadoria (`--fail-on-error`).

## Procedimento

1. `pip install -r requirements.txt`
2. `python -m scripts.sincronizar_imagens --fail-on-error` (a Wikimedia
   limita taxa de requisição — se aparecerem muitos `429`, rodar de novo com
   `--workers 1`; o script é idempotente e retoma só o que faltou).
3. Enviar `app/static/img-acervo/` ao bucket preservando o prefixo
   `img-acervo/` (o script não inclui cliente S3 — não é dependência de
   runtime da API; usar `boto3`/`aws s3 sync`/`rclone` apontando pro
   endpoint S3 do provedor).
4. Commitar `app/data/image-manifest.json` no Git. Diferente dos `.webp`
   (que ficam só no bucket, ver `.gitignore`), o manifesto é só metadado —
   pequeno e versionado — porque a API precisa dele presente no boot para
   resolver as URLs; sem um pipeline que rode o sincronizador a cada deploy,
   um manifesto ausente faz a API cair ao subir com `IMAGE_CDN_BASE_URL`
   configurada (ver `app/image_assets.py`).
5. Configurar `IMAGE_CDN_BASE_URL=https://cdn.seu-dominio.com` no ambiente
   da API (a variável já está declarada em `render.yaml`; preencher o valor
   no dashboard do Render) e publicar.

Para validar sem gravar arquivos, use `--dry-run --limit 10`. O diretório local também pode ser exposto pela API em `/img-acervo` para homologação.
