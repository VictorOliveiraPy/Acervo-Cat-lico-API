# Conteúdo do Instagram — Compêndio Católico

Calendário de conteúdo pronto pra postar: 38 posts de curiosidade (imagem +
legenda), 8 memes, 2 carrosséis de "história", 10 roteiros de Reels e 6
formatos de Stories, organizados por categoria/formato.

## Identidade visual

A imagem de cada peça replica o mesmo estilo já usado nos posts de citação
do Compêndio Católico (referência em `_gerador/arte/referencia-identidade.png`
e em `post-velas.png`, na raiz do repo):
fundo bordô com vinheta, moldura fina dourada, título em **Playfair
Display** (serifada, bold) e corpo em **EB Garamond** — e, em toda imagem,
**o selo da marca**: o círculo duplo dourado com o "C" no centro. Cada
categoria de post também tem um ícone dourado próprio (cálice, auréola,
cruz, livro, lamparina, globo).

Nenhum formato fica só em texto — todos têm imagem pronta:

- **Posts** (`posts/<categoria>/NN-titulo.png`): card completo com ícone,
  título e texto.
- **Memes** (`memes/`): texto bold sobre arte sacra clássica de domínio
  público, em vez de fotos de terceiros com direitos reservados.
- **Histórias** (`historias/`): carrossel (capa com a pintura + slides de
  texto + CTA), na mesma moldura bordô/dourada.
- **Reels** (`reels/<NN-slug>/cena-N.jpg`): um card por cena do roteiro,
  pra usar direto ou como base pra editar no CapCut/InShot.
- **Stories** (`stories/<NN-slug>/slide-N.jpg`): um card por slide, com uma
  caixa indicando onde colar o sticker nativo do Instagram (quiz, enquete,
  contagem regressiva...).

Pra gerar tudo de novo (depois de editar os textos):

```bash
python marketing/instagram/_gerador/gerar_tudo.py       # os 38 posts
python marketing/instagram/_gerador/gerar_memes.py       # os 8 memes
python marketing/instagram/_gerador/gerar_historias.py   # os 2 carrosséis
python marketing/instagram/_gerador/gerar_cards.py       # cenas de Reels + slides de Stories
```

Não precisa de internet pra rodar — as fontes (Playfair Display e EB Garamond,
licença OFL) e as pinturas (domínio público, ver `_gerador/arte/SOURCES.md`)
já estão versionadas em `_gerador/`.

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
├── memes/                    (8 memes + legendas.md)
├── historias/
│   ├── filho-prodigo/        (carrossel de 5 slides + legenda.md)
│   └── paixao-em-4-atos/     (carrossel de 6 slides + legenda.md)
├── reels/
│   └── NN-slug/               (roteiro.md + cena-1.jpg ... cena-4.jpg)
├── stories/
│   └── NN-slug/               (roteiro.md + slide-1.jpg ... slide-N.jpg)
└── _gerador/        (scripts + fontes + pinturas — gera tudo acima)
```

Cada post de curiosidade tem dois arquivos com o mesmo nome: `NN-titulo.png`
(a imagem pronta) e `NN-titulo.md` (legenda pronta pra copiar, hashtags e uma
sugestão de foto/arte alternativa). Memes e histórias têm a legenda/hashtags
num `legendas.md`/`legenda.md` só na pasta. Cada Reel/Story tem sua própria
pasta com o `roteiro.md` e as imagens de cada cena/slide juntas.

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

Isso vale também pra qualquer imagem de referência salva em `img_insta/` (fora
do Git, ver `.gitignore`): são screenshots de terceiros pra inspiração de
formato/tom, não material pra reutilizar direto. Os memes deste calendário
usam arte sacra clássica de domínio público (créditos em
`_gerador/arte/SOURCES.md`) em vez de frames de produções com direitos
reservados — mesmo formato de humor, sem o risco.

## Áudio de Reels

Use a biblioteca de músicas do próprio Instagram/Reels (já licenciada pra uso
na plataforma) em vez de trilha extraída de filme ou série.
