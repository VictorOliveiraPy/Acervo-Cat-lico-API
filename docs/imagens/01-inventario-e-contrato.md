# Tarefa 1 ? Invent?rio e contrato de imagens

**Status:** conclu?da

## Objetivo

Definir um contrato est?vel entre o conte?do editorial, o sincronizador e o frontend sem substituir nem perder a URL original da Wikimedia.

## Requisitos

- Manter `imagem` e `imagem_credito` nos JSONs como fonte editorial.
- Criar um manifesto versionado que relacione URL de origem e caminho p?blico do asset gerado.
- Usar nomes determin?sticos para que a mesma URL n?o seja baixada duas vezes.
- Preservar os cr?ditos existentes no conte?do; a licen?a continua sendo responsabilidade da curadoria antes da publica??o.

## Entrega

O formato do manifesto ? `{"version": 1, "images": {URL: {"path": ...}}}`. O caminho ? sempre relativo ao CDN, sob `/img-acervo/`.
