# Tarefa 3 ? Resolu??o de URL na API

**Status:** conclu?da

## Objetivo

Fazer a API servir URLs do CDN ap?s a sincroniza??o, mas manter o comportamento atual enquanto o CDN ainda n?o estiver configurado.

## Requisitos

- Ler e validar o manifesto no carregamento do acervo.
- Trocar somente URLs presentes no manifesto.
- Exigir `IMAGE_CDN_BASE_URL` para ativar a troca; sem ela a URL editorial original ? devolvida, permitindo rollout sem quebra.
- Falhar cedo se o CDN for configurado com manifesto inv?lido ou ausente.
- Aplicar a mesma regra ao conte?do traduzido.

## Entrega

`app/image_assets.py`, configura??o em `app/config.py` e testes unit?rios de resolu??o e de integra??o com o reposit?rio.
