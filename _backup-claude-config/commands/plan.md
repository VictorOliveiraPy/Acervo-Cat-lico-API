---
description: Restate requirements, assess risks, and create step-by-step implementation plan. WAIT for user CONFIRM before touching any code.
argument-hint: "[feature description]"
---

# Plan Command

Creates a comprehensive implementation plan before writing any code.

## What This Command Does

1. **Restate Requirements** - Clarify what needs to be built
2. **Identify Risks** - Surface potential issues and blockers
3. **Create Step Plan** - Break down implementation into phases
4. **Wait for Confirmation** - MUST receive user approval before proceeding

## How It Works

1. Analyze the request and restate requirements in clear terms
2. Search the codebase for existing patterns to mirror
3. Break down into phases with specific, actionable steps
4. Identify dependencies between components
5. Assess risks and potential blockers
6. Estimate complexity (High/Medium/Low)
7. Present the plan and WAIT for explicit confirmation

## Pattern Grounding

Before writing the plan, search the codebase for conventions to mirror:

| Category | What to capture |
|---|---|
| Naming | File, function, type naming in the affected area |
| Error handling | How failures are raised, returned, or logged |
| Data access | Repository, service, query patterns |
| Tests | Test file location, framework, assertion style |

## Plan Output Format

```markdown
# Implementation Plan: {Feature Name}

## Requirements Restatement
- {clear bullet points}

## Implementation Phases

### Phase 1: {Name}
- {specific steps}

### Phase 2: {Name}
- {specific steps}

## Dependencies
- {list of dependencies}

## Risks
- HIGH: {risk description}
- MEDIUM: {risk description}

## Estimated Complexity: HIGH | MEDIUM | LOW

**WAITING FOR CONFIRMATION**: Proceed with this plan? (yes/no/modify)
```

## CRITICAL

This command will **NOT** write any code until you explicitly confirm the plan.

## Integration

After planning:
- Use `/build-fix` if build errors occur during implementation
- Use `/code-review` to review completed implementation
