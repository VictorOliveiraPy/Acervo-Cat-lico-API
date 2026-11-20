#!/usr/bin/env node
/**
 * Quality Gate — PostToolUse hook
 * Runs after file edits (Write/Edit) to catch common issues.
 * Always exits 0 (non-blocking), outputs warnings to stderr.
 */

const fs = require('fs');

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

  const toolName = event.tool_name || '';
  const toolInput = event.tool_input || {};

  if (!['Write', 'Edit'].includes(toolName)) {
    process.exit(0);
  }

  const filePath = toolInput.file_path || '';
  const content = toolInput.content || toolInput.new_string || '';

  if (!filePath || !content) {
    process.exit(0);
  }

  const ext = filePath.split('.').pop() || '';
  const isCode = ['js', 'ts', 'jsx', 'tsx', 'py', 'go', 'rs'].includes(ext);

  if (!isCode) process.exit(0);

  const warnings = [];

  // Detect console.log (JS/TS only)
  if (['js', 'ts', 'jsx', 'tsx'].includes(ext)) {
    const consoleMatches = (content.match(/console\.(log|debug|info)\(/g) || []).length;
    if (consoleMatches > 0) {
      warnings.push(`[quality-gate] ${filePath}: ${consoleMatches} console.log/debug/info statement(s) detected — remove before committing`);
    }
  }

  // Detect hardcoded secrets patterns
  const secretPatterns = [
    { pattern: /(['"])sk-[a-zA-Z0-9]{20,}\1/, label: 'OpenAI/Anthropic API key' },
    { pattern: /(['"])ghp_[a-zA-Z0-9]{36}\1/, label: 'GitHub personal access token' },
    { pattern: /(['"])AKIA[0-9A-Z]{16}\1/, label: 'AWS access key ID' },
    { pattern: /password\s*=\s*['"][^'"]{6,}['"]/, label: 'hardcoded password' },
    { pattern: /secret\s*=\s*['"][^'"]{6,}['"]/, label: 'hardcoded secret' },
    { pattern: /api[_-]?key\s*[=:]\s*['"][^'"]{8,}['"]/i, label: 'hardcoded API key' },
  ];

  for (const { pattern, label } of secretPatterns) {
    if (pattern.test(content)) {
      warnings.push(`[quality-gate] ${filePath}: possible ${label} detected — use environment variables instead`);
    }
  }

  // Detect TODO without ticket reference
  const todoLines = content.split('\n').filter(line =>
    /TODO|FIXME|HACK/.test(line) && !/TODO.*#\d+|TODO.*\w+-\d+/.test(line)
  );
  if (todoLines.length > 0) {
    warnings.push(`[quality-gate] ${filePath}: ${todoLines.length} TODO/FIXME without ticket reference`);
  }

  if (warnings.length > 0) {
    process.stderr.write(warnings.join('\n') + '\n');
  }

  process.exit(0);
}

main();
