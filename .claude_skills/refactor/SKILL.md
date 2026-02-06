---
name: refactor
description: Intelligently refactor code - improve structure, readability, and maintainability without changing behavior
argument-hint: [file-path or component-name] [optional:focus-area]
context: fork
agent: general-purpose
allowed-tools: Read, Write, Glob, Grep, Bash
---

# Code Refactoring Assistant

Refactor: **$ARGUMENTS**

## Golden Rules

1. **Behavior must not change** - Same inputs = same outputs
2. **Small steps** - One refactoring at a time
3. **Test after each change** - If tests exist, run them
4. **When in doubt, don't** - Ask before risky changes

## Analysis Phase

First, understand the code:

1. **Read the entire file/component**
2. **Identify code smells**:
   - Functions > 30 lines
   - Deep nesting (> 3 levels)
   - Duplicate code
   - Long parameter lists
   - Mixed responsibilities
   - Magic numbers/strings
   - Complex conditionals

3. **Check for tests** - They're your safety net

## Refactoring Catalog

### Extract Function
**When**: Code block does one distinct thing
```typescript
// Before
function process() {
  // 20 lines of validation
  // 20 lines of transformation
}

// After
function process() {
  validate();
  transform();
}
```

### Simplify Conditionals
**When**: Complex if/else chains
```typescript
// Before
if (status === 'active' && role === 'admin' && !suspended) { ... }

// After
const canAccess = status === 'active' && role === 'admin' && !suspended;
if (canAccess) { ... }

// Or even better
function canAccess(user) { return ... }
```

### Replace Magic Values
**When**: Hardcoded numbers/strings with meaning
```typescript
// Before
if (retries > 3) { ... }

// After
const MAX_RETRIES = 3;
if (retries > MAX_RETRIES) { ... }
```

### Consolidate Duplicates
**When**: Same code appears 2+ times
```typescript
// Extract into reusable function
// Place in appropriate shared location
```

### Improve Naming
**When**: Names don't reveal intent
```typescript
// Before
const d = new Date() - startDate;

// After
const elapsedTime = new Date() - startDate;
```

### Flatten Nesting
**When**: Arrow code (deep indentation)
```typescript
// Before
if (user) {
  if (user.isActive) {
    if (user.hasPermission) {
      doThing();
    }
  }
}

// After (early returns)
if (!user) return;
if (!user.isActive) return;
if (!user.hasPermission) return;
doThing();
```

## Process

1. **List all identified issues** with line numbers
2. **Prioritize** by impact and risk
3. **Propose changes** before making them
4. **Apply refactorings** one at a time
5. **Show before/after** for each change
6. **Run tests** if available

## Output Format

```
## Issues Found
1. [Line X] Description of issue
2. [Line Y] Description of issue

## Proposed Changes
1. Change A - Low risk
2. Change B - Medium risk (explain why)

## Changes Made
### 1. [Description]
- Before: ...
- After: ...
- Why: ...
```

## Safety Checks

- [ ] No behavior changes
- [ ] All tests still pass (if applicable)
- [ ] No new dependencies introduced
- [ ] Code is genuinely simpler (not just different)
