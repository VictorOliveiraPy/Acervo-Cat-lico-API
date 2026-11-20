---
description: Code review — local uncommitted changes or GitHub PR (pass PR number/URL for PR mode)
argument-hint: [pr-number | pr-url | blank for local review]
---

# Code Review

**Input**: $ARGUMENTS

## Mode Selection

If `$ARGUMENTS` contains a PR number, PR URL, or `--pr`:
→ Jump to **PR Review Mode** below.

Otherwise:
→ Use **Local Review Mode**.

---

## Local Review Mode

Comprehensive security and quality review of uncommitted changes.

### Phase 1 — GATHER

```bash
git diff --name-only HEAD
```

If no changed files, stop: "Nothing to review."

### Phase 2 — REVIEW

Read each changed file in full. Check for:

**Security Issues (CRITICAL):**
- Hardcoded credentials, API keys, tokens
- SQL injection vulnerabilities
- XSS vulnerabilities
- Missing input validation
- Path traversal risks

**Code Quality (HIGH):**
- Functions > 50 lines
- Files > 800 lines
- Nesting depth > 4 levels
- Missing error handling
- console.log statements
- TODO/FIXME without ticket references
- Missing tests for new code

**Best Practices (MEDIUM):**
- Mutation patterns (use immutable instead)
- Missing accessibility (a11y)

### Phase 3 — REPORT

Generate report with:
- Severity: CRITICAL, HIGH, MEDIUM, LOW
- File location and line numbers
- Issue description
- Suggested fix

Block commit if CRITICAL or HIGH issues found.
Never approve code with security vulnerabilities.

---

## PR Review Mode

Comprehensive GitHub PR review — fetches diff, reads full files, runs validation, posts review.

### Phase 1 — FETCH

```bash
gh pr view <NUMBER> --json number,title,body,author,baseRefName,headRefName,changedFiles,additions,deletions
gh pr diff <NUMBER>
```

### Phase 2 — REVIEW

Apply review checklist:

| Category | What to Check |
|---|---|
| **Correctness** | Logic errors, null handling, edge cases |
| **Type Safety** | Type mismatches, unsafe casts, `any` usage |
| **Security** | Injection, auth gaps, secret exposure, XSS |
| **Performance** | N+1 queries, unbounded loops, memory leaks |
| **Completeness** | Missing tests, error handling, docs |

### Phase 3 — VALIDATE

Detect project type and run:

**Node.js/TypeScript:**
```bash
npx tsc --noEmit
npm run lint
npm test
```

**Go:**
```bash
go vet ./...
go test ./...
```

**Python:**
```bash
pytest
ruff check .
```

**Rust:**
```bash
cargo clippy -- -D warnings
cargo test
```

### Phase 4 — DECIDE & REPORT

| Condition | Decision |
|---|---|
| Zero CRITICAL/HIGH | **APPROVE** |
| HIGH issues only | **REQUEST CHANGES** |
| Any CRITICAL | **BLOCK** |

Post review to GitHub:
```bash
gh pr review <NUMBER> --approve --body "<summary>"
gh pr review <NUMBER> --request-changes --body "<summary>"
```
