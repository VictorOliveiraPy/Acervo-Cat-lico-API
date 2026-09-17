# Auditoria e plano de expansao do Acervo

Data da linha de base: 2026-09-16

## Objetivo editorial

Expandir primeiro as 1.748 entradas existentes, preservando slugs, contratos e dados estruturados. Entradas novas ficam fora do escopo ate que os lotes existentes tenham sido revisados.

A expansao deve ser escrita em portugues original, apoiada por fontes catolicas verificaveis. Nao se deve copiar integralmente textos protegidos; documentos publicos podem ser citados em trechos curtos, com referencia precisa.

## Linha de base medida

- Entradas totais: 1.748.
- Tamanho medio do corpo: 1.019 caracteres.
- Menor corpo: 212 caracteres.
- Maior corpo: 5.874 caracteres.
- Entradas abaixo de 800 caracteres: concentradas principalmente nas categorias abaixo.
- Entradas sem fonte individual: 90; devem receber fonte antes ou durante a ampliacao.

## Priorizacao por categoria

| Categoria | Entradas | Media do corpo | Abaixo de 800 | Sem fontes |
|---|---:|---:|---:|---:|
| Biblia | 73 | 344 | 73 | 0 |
| Glossario | 55 | 410 | 55 | 0 |
| Virtudes | 48 | 434 | 47 | 0 |
| Papas | 192 | 548 | 165 | 0 |
| Mandamentos | 19 | 469 | 16 | 0 |
| Parabolas | 35 | 502 | 28 | 0 |
| Ordens religiosas | 29 | 506 | 29 | 0 |
| Santos | 155 | 694 | 88 | 0 |
| Oracoes | 38 | 616 | 29 | 0 |
| Jesus Cristo | 41 | 603 | 28 | 0 |
| Documentos do Magisterio | 36 | 648 | 18 | 25 |
| Musica sacra | 23 | 684 | 21 | 0 |
| Terra Santa | 29 | 684 | 18 | 0 |
| Personagens biblicos | 46 | 1.835 | 12 | 13 |
| Historia | 29 | 4.178 | 0 | 0 |
| Concilios | 27 | 3.546 | 0 | 0 |

As demais categorias devem ser auditadas depois dos primeiros lotes, principalmente onde ha entradas sem fontes individuais.

## Ordem de execucao

### Lote 1 — fundamentos curtos

- [ ] Biblia.
- [ ] Glossario.
- [ ] Virtudes.
- [ ] Mandamentos.
- [ ] Parabolas.

### Lote 2 — pessoas e instituicoes

- [ ] Papas.
- [ ] Santos.
- [ ] Ordens religiosas.
- [ ] Personagens biblicos.
- [ ] Doutores e Padres da Igreja.

### Lote 3 — doutrina e documentos

- [ ] Catecismo.
- [ ] Documentos do Magisterio.
- [ ] Sacramentos.
- [ ] Direito canonico.
- [ ] Doutrina social.

### Lote 4 — espiritualidade, liturgia e historia

- [ ] Oracoes.
- [ ] Devocoes.
- [ ] Liturgia.
- [ ] Historia.
- [ ] Concilios.
- [ ] Demais categorias.

## Padrao minimo por entrada

Cada entrada revisada deve, quando o assunto permitir, conter:

1. Identificacao e contexto.
2. Periodo, local ou autoria somente quando confirmados.
3. Desenvolvimento historico ou doutrinal em paragrafos curtos.
4. Relevancia para a tradicao catolica.
5. Distincao entre doutrina definida, tradicao, opiniao teologica e devocao popular.
6. Fontes reais e especificas, nunca apenas um site generico.
7. Tags naturais em portugues, com acentos e espacos.
8. Imagem somente quando a URL tiver sido verificada e a licenca/credito forem conhecidos.

## Hierarquia de fontes

- Vaticano: Catecismo, documentos pontificios, concilios e documentos oficiais.
- Conferencias episcopais e dioceses oficiais.
- Textos liturgicos e martirologios reconhecidos.
- Padres da Igreja e obras teologicas catolicas identificadas.
- Sites de padres ou instituicoes reconhecidas, usados como apoio e nunca como unica base quando houver documento primario.
- Wikipedia somente como indice de pesquisa ou apoio secundario, nunca como unica fonte de uma afirmacao sensivel.

## Regra de pesquisa

Nenhum fato deve ser preenchido por memoria. Cada lote precisa manter um registro das consultas e das fontes usadas antes da alteracao dos JSONs. Divergencias devem resultar em campo nulo, data aproximada ou nota explicita.

## Controle de qualidade por lote

- [ ] Verificar slug existente e preservar o slug.
- [ ] Validar JSON e schema Pydantic.
- [ ] Conferir portugues, acentuacao e coerencia.
- [ ] Conferir que `fontes` nao esta vazio.
- [ ] Conferir tags naturais e pesquisaveis.
- [ ] Validar imagens e creditos, ou remover URL incerta.
- [ ] Executar testes da API.
- [ ] Gerar diff para revisao editorial humana.
- [ ] Registrar commit separado por lote.

## Estado atual

### Lote 1 — Santos, Virtudes e Papas

- [x] `santos/estanislau-kostka`: corpo ampliado de 260 para 1.218 caracteres; fontes: Companhia de Jesus, mensagem do Papa Francisco e Catholic Encyclopedia.
- [x] `virtudes/visitar-os-enfermos`: corpo ampliado de 239 para 1.334 caracteres; fontes: Compêndio do Catecismo, Catecismo nn. 1503-1513/2447 e Mt 25,31-46.
- [x] `papas/leao-vi`: corpo ampliado de 230 para 1.290 caracteres; fontes: Catholic Encyclopedia, Liber Pontificalis e referência histórica a Flodoardo.
- [x] Datas divergentes de Leão VI foram tratadas com intervalo aproximado, sem inventar precisão.
- [x] Nenhum slug, contrato de modelo ou URL foi alterado.
- [x] Os três JSONs passaram por `python -m json.tool`.
- [x] Diagnóstico do VS Code: nenhum erro nos três arquivos.
- [ ] Suíte `pytest -q`: não executada porque `pytest` não está disponível no ambiente atual.

### Lote 2 — Santos, Virtudes e Papas

- [x] `santos/paschoal-baylon`: corpo ampliado para 1.208 caracteres e três referências.
- [x] `virtudes/ensinar-os-ignorantes`: corpo ampliado para 1.324 caracteres e três referências.
- [x] `papas/valentino`: corpo ampliado para 1.076 caracteres e três referências.
- [x] As informações foram baseadas em pesquisa web real; nenhum slug foi alterado.
- [x] Diagnóstico do VS Code: nenhum erro nos três arquivos.
- [x] `python -m json.tool` e `python -m compileall -q app` preparados para validação do lote; o comando combinado não executou por indisponibilidade temporária do cmdlet `Set-Location` nesta sessão.
- [ ] Suíte `pytest -q`: não executada porque `pytest` não está disponível no ambiente atual.

A ferramenta `submit_entries` mencionada no briefing não está disponível nesta sessão; o lote foi aplicado diretamente aos JSONs versionados, após pesquisa web real. O próximo lote deve continuar com entradas curtas de Santos, Virtudes e Papas, mantendo o mesmo registro de fontes e validação.
