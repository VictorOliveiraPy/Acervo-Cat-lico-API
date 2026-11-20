---
paths:
  - "**/*.tsx"
  - "**/*.jsx"
  - "**/components/**/*.ts"
  - "**/hooks/**/*.ts"
---
# React Coding Style

> Extends typescript/coding-style.md with React specific content.

## File Extensions

- `.tsx` for any file containing JSX
- `.ts` for pure logic, custom hooks without JSX, utilities
- `.test.tsx` / `.test.ts` mirroring the source file

## Naming

- Components: `PascalCase` for symbol and file (`UserCard.tsx`)
- Custom hooks: `useCamelCase` (`useDebounce`)
- Event handlers: `handleClick`, `handleSubmit` inside the component
- Boolean props: `isLoading`, `hasError`, `canSubmit`

## Component Shape

```tsx
type Props = {
  user: User;
  onSelect: (id: string) => void;
};

export function UserCard({ user, onSelect }: Props) {
  return (
    <button type="button" onClick={() => onSelect(user.id)}>
      {user.name}
    </button>
  );
}
```

- Always destructure props in the parameter list
- Prefer `type Props = {}` for closed component prop shapes

## JSX

- Self-close tags with no children: `<UserCard user={u} />`
- Use fragments `<>...</>` over wrapper `<div>` when no DOM element is needed
- Conditional rendering: `{condition && <Foo />}` for booleans, ternary for either/or

## Hooks Discipline

- Custom hooks must start with `use`
- Group all hook calls at the top of the component, before any conditional logic
- Complete all dependencies in `useEffect`/`useMemo`/`useCallback`

```tsx
// WRONG: Missing dependency
useEffect(() => {
  fetchData(userId);
}, []); // userId missing from deps

// CORRECT
useEffect(() => {
  fetchData(userId);
}, [userId]);
```

## State

- Local first (`useState`), lift only when shared
- Context for cross-cutting state (theme, auth)
- External store (Zustand, Jotai) when state persists across routes
- Never duplicate state that can be derived

## Class Components

Forbidden in new code. Convert to function components when touching them.

## Server / Client Boundary (Next.js)

- Default to Server Component — add `"use client"` only when using state, effects, or event handlers
- Place `"use client"` on line 1, before imports
