# Conteúdo do Instagram — Compêndio Católico

Calendário de conteúdo pronto pra postar: 38 posts estáticos (imagem + legenda),
10 roteiros de Reels e 6 formatos de Stories, organizados por categoria.

## Identidade visual

A imagem de cada post replica o mesmo estilo já usado no mural de velas
(`post-velas.png`, na raiz do repo): fundo bordô com vinheta, moldura fina
dourada, título em **Playfair Display** (serifada, bold) e corpo em
**EB Garamond**, sempre com `compendio-catolico.com` no rodapé. Cada categoria
tem um ícone dourado próprio (cálice, auréola, cruz, livro, lamparina, globo).

As imagens já vêm prontas em `posts/<categoria>/NN-titulo.png` (1080×1350,
formato de post do Instagram). Pra gerar de novo (depois de editar
`_gerador/dados.py` com posts novos ou textos revisados):

```bash
python marketing/instagram/_gerador/gerar_tudo.py
```

Não precisa de internet pra rodar — as fontes (Playfair Display e EB Garamond,
licença OFL) já estão em `_gerador/fonts/`.

## Estrutura

```
marketing/instagram/
├── posts/
│   ├── missa/       (5 posts)
│   ├── santos/      (6 posts)
│   ├── padres/      (4 posts)
│   ├── historia/    (7 posts)
│   ├── chosen/      (8 posts)
│   └── mundo/       (8 posts)
├── reels/           (10 roteiros, .md)
├── stories/         (6 formatos, .md)
└── _gerador/        (script que gera as imagens dos posts)
```

Cada post tem dois arquivos com o mesmo nome: `NN-titulo.png` (a imagem
pronta) e `NN-titulo.md` (legenda pronta pra copiar, hashtags e uma sugestão
de foto/arte alternativa, caso queira variar em vez de usar a imagem gerada).

## Direitos autorais — leia antes de postar sobre The Chosen ou pessoas reais

Os posts de **The Chosen** e de **Mundo Católico** (atletas, artistas, times)
falam de produções e pessoas que não são do Compêndio Católico:

- **Nunca** baixe/reposte frames da série, fotos de imprensa de atletas/artistas
  ou logos de clubes como se fossem seus — é risco real de denúncia e
  derrubada de conteúdo, não só uma formalidade.
- As imagens já geradas (`posts/chosen/*.png`, `posts/mundo/*.png`) são cards
  de texto autorais — não usam nenhuma foto de terceiros — exatamente por
  esse motivo, e podem ser postadas como estão.
- Se quiser usar uma foto real da pessoa/produção em vez do card, prefira:
  repost oficial marcando a fonte, imagem de kit de imprensa liberado, ou uma
  foto de banco licenciado para uso editorial.
- Fé de pessoas vivas é informação sensível: só entraram no calendário nomes
  com fé católica amplamente documentada e pública (declarações próprias,
  reportagens consistentes) — evite adicionar novos nomes sem essa mesma
  checagem.

## Áudio de Reels

Use a biblioteca de músicas do próprio Instagram/Reels (já licenciada pra uso
na plataforma) em vez de trilha extraída de filme ou série.
