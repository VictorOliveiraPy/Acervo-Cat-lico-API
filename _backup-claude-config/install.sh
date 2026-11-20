#!/usr/bin/env bash
# Liga este repo ao ~/.claude para que agents, comandos, regras e hooks valham em todos os projetos.
set -euo pipefail
REPO="$(cd "$(dirname "$0")" && pwd)"
mkdir -p ~/.claude
for d in agents commands rules hooks; do
  t=~/.claude/$d
  if [ -e "$t" ] && [ ! -L "$t" ]; then mv "$t" "$t.bak.$(date +%s)"; fi
  ln -sfn "$REPO/$d" "$t"
done
# skills: ~/.claude/skills tem conteúdo sincronizado da conta, então liga cada skill individualmente
mkdir -p ~/.claude/skills
for s in "$REPO"/skills/*/; do [ -d "$s" ] && ln -sfn "${s%/}" ~/.claude/skills/"$(basename "$s")"; done
echo "Pronto. Hooks: veja settings.hooks.json e mescle em ~/.claude/settings.json se ainda não estiver."
