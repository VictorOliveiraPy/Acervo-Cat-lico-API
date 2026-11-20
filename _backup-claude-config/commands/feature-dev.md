---
description: Guided feature development with codebase understanding and architecture focus
---

A structured feature-development workflow that emphasizes understanding existing code before writing new code.

## Phases

### 1. Discovery

- Read the feature request carefully
- Identify requirements, constraints, and acceptance criteria
- Ask clarifying questions if the request is ambiguous

### 2. Codebase Exploration

- Explore the relevant existing code with Read, Grep, and Glob tools
- Trace execution paths and architecture layers
- Understand integration points and conventions

### 3. Clarifying Questions

- Present findings from exploration
- Ask targeted design and edge-case questions
- Wait for user response before proceeding

### 4. Architecture Design

- Design the feature based on existing patterns found
- Provide the implementation blueprint
- Wait for approval before implementing

### 5. Implementation

- Implement the feature following the approved design
- Prefer TDD where appropriate
- Keep commits small and focused

### 6. Quality Review

- Review the implementation for quality and security
- Address critical and important issues
- Verify test coverage

### 7. Summary

- Summarize what was built
- List follow-up items or limitations
- Provide testing instructions
