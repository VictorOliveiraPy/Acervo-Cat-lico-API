# claude-config

Configuração global do Claude Code: agents, comandos, regras e hooks que valem em todos os projetos.

## Instalar (máquina nova / depois de formatar)

```bash
git clone git@github.com:VictorOliveiraPy/claude-config.git ~/projects/claude-config
~/projects/claude-config/install.sh
```

Depois mescle `settings.hooks.json` em `~/.claude/settings.json`.

## Conteúdo

- `agents/` — code-reviewer, security-reviewer, tdd-guide, build-error-resolver
- `commands/` — /plan, /code-review, /feature-dev, /build-fix
- `rules/` — estilo React e TypeScript
- `hooks/` — pre-bash-guard (bloqueia comandos destrutivos), quality-gate (avisa console.log e segredos no código)
- `skills/` — skills próprias (pasta `<nome>/SKILL.md`)

Para adicionar algo: crie o arquivo aqui, faça commit e push. Como `~/.claude/*` aponta para cá, já vale na hora.
