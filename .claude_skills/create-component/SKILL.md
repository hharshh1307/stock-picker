---
name: create-component
description: Generate a production-ready React/Next.js component with TypeScript, proper types, accessibility, and optional tests
argument-hint: [ComponentName] [optional:description]
context: fork
agent: frontend-engineer
allowed-tools: Read, Write, Glob, Grep, Bash(npm:*), Bash(npx:*)
---

# Component Generator

Create a production-ready component named **$ARGUMENTS**.

## Steps

1. **Analyze the codebase** to understand:
   - Existing component patterns in `src/components/` or similar
   - Styling approach (Tailwind, CSS Modules, styled-components)
   - TypeScript conventions and prop patterns
   - Test file locations and patterns

2. **Create the component** with:
   - TypeScript interface for props
   - Proper default exports
   - Semantic HTML elements
   - Accessibility attributes (aria-labels, roles, keyboard navigation)
   - Responsive design considerations

3. **Follow project conventions**:
   - Match existing file naming (PascalCase vs kebab-case)
   - Use existing design tokens/variables
   - Follow established patterns for loading/error states

4. **Component structure**:
```tsx
interface ComponentNameProps {
  // Required props first
  // Optional props with defaults
  className?: string;
}

export function ComponentName({ className, ...props }: ComponentNameProps) {
  return (
    // Implementation
  );
}
```

5. **If tests are needed**, create with:
   - Render test
   - User interaction tests
   - Accessibility checks

## Quality Checklist
- [ ] Props are properly typed
- [ ] Component is accessible
- [ ] Follows existing project patterns
- [ ] No hardcoded strings (use props or constants)
- [ ] Handles edge cases (empty states, loading, errors)
