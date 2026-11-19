# Compêndio Católico — API (FastAPI)

Serve o acervo, a liturgia, os perfis e o chat para o front em `../Acervo-Cat-lico-Web`.
O conteúdo vive em `app/data/*.json` (português, canônico) e
`app/data/i18n/<idioma>/` (traduções, validadas pelo mesmo modelo `Dataset`).

## Comandos

```bash
make lint          # ruff
make typecheck     # mypy
make test          # pytest com cobertura (mínimo 70%)
make mutation      # testes mutantes (mutmut) em app/domain
python -m scripts.traduzir_acervo --idiomas en   # traduz o acervo pelo `claude -p`
```

Publicar: `../Acervo-Cat-lico-Web/deploy/publicar.sh api`.

## Como trabalhar

**TDD em três camadas.** O teste vem antes do código:
- **Unitário** para regra de negócio em `app/domain` (ex.: `profiles/progression.py`).
  Regra nova nasce ali, pura, e ganha teste em `tests/domain`.
- **Integração** para cada rota: `tests/interface`, com o `TestClient`. Rota nova ou
  contrato mudado ganha teste ali antes do código.
- **E2E** das jornadas fica no front (`e2e/` de lá).

**Testes mutantes:** depois de mexer em `app/domain`, rode `make mutation` e mate os
mutantes que sobreviverem naquele módulo com testes novos.

**Pronto** é: lint, typecheck e testes passando.

## Modelos e subagentes

- Edição de código fica no modelo principal (Opus 5.5), começando em esforço `medium`.
- Leitura barata vai para os subagentes Haiku de `.claude/agents/`: `explorador` e
  `leitor-de-logs`.
- Trabalho paralelo e independente vai para um worker do Orca, no seu worktree.

## Cuidados

- Nunca mude `id` ou `slug` de um verbete sem procurar referências no front: são URLs
  indexadas.
- Tradução nova só entra em `SUPPORTED_LANGUAGES` (`app/infrastructure/acervo/translations.py`)
  depois que a pasta do idioma existir.
