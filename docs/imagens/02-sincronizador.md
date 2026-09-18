# Tarefa 2 ? Sincronizador de pr?-publica??o

**Status:** conclu?da

## Objetivo

Baixar previamente as imagens remotas, validar a resposta e gerar vers?es WebP pr?prias antes do deploy.

## Requisitos

- Percorrer todos os JSONs, inclusive tradu??es, e deduplicar URLs.
- Rejeitar respostas sem tipo de imagem, arquivos maiores que o limite e formatos que o processador n?o consegue abrir.
- Redimensionar sem ampliar, converter para WebP e gravar de forma at?mica.
- Ser idempotente: um asset j? presente e registrado n?o ? baixado novamente.
- Possuir `--dry-run`, limite de concorr?ncia, timeout, retry e relat?rio de falhas; nenhuma altera??o em JSONs editoriais.

## Entrega

`python -m scripts.sincronizar_imagens` gera `app/data/image-manifest.json` e assets em `app/static/img-acervo/`. Esses arquivos podem ser enviados ao bucket ou CDN no mesmo passo do pipeline de publica??o.
