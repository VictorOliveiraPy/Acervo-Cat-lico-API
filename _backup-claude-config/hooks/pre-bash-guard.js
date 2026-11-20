#!/usr/bin/env node
/**
 * Pre-Bash Guard — PreToolUse hook
 * Blocks dangerous bash commands before they execute.
 * Exit code 2 = block the tool call and show the message.
 * Exit code 0 = allow the tool call.
 */

const fs = require('fs');

const DANGEROUS_PATTERNS = [
  { pattern: /rm\s+-rf\s+\/(?!\S)/, label: 'rm -rf / (delete root filesystem)' },
  { pattern: /rm\s+-rf\s+~(?:\/|$|\s)/, label: 'rm -rf ~ (delete home directory)' },
  { pattern: /git\s+push\s+.*--force(?:\s|$)/, label: 'force push (can overwrite remote history)' },
  { pattern: /git\s+reset\s+--hard\s+HEAD~[2-9]/, label: 'git reset --hard (drops multiple commits)' },
  { pattern: /DROP\s+(?:TABLE|DATABASE)\s+(?!.*IF\s+EXISTS)/i, label: 'DROP TABLE/DATABASE without IF EXISTS' },
  { pattern: /chmod\s+-R\s+777/, label: 'chmod -R 777 (insecure permissions)' },
];

function main() {
  let input = '';
  try {
    input = fs.readFileSync('/dev/stdin', 'utf8');
  } catch {
    process.exit(0);
  }

  let event;
  try {
    event = JSON.parse(input);
  } catch {
    process.exit(0);
  }

  if (event.tool_name !== 'Bash') {
    process.exit(0);
  }

  const command = (event.tool_input || {}).command || '';

  for (const { pattern, label } of DANGEROUS_PATTERNS) {
    if (pattern.test(command)) {
      const msg = JSON.stringify({
        decision: 'block',
        reason: `[pre-bash-guard] Blocked: ${label}\nCommand: ${command.slice(0, 100)}\n\nIf you really need to run this, confirm explicitly.`
      });
      process.stderr.write(JSON.parse(msg).reason + "\n");
      process.exit(2);
    }
  }

  process.exit(0);
}

main();
