---
name: debug-detective
description: Systematically investigate and solve bugs using detective methodology - find root cause, not just symptoms
argument-hint: [bug-description or error-message]
context: fork
agent: general-purpose
allowed-tools: Read, Write, Glob, Grep, Bash
---

# Debug Detective

Investigating: **$ARGUMENTS**

## The Detective Method

```
        Observe
           │
           ▼
    Form Hypothesis
           │
           ▼
     Test Theory ──────┐
           │           │
           ▼           │
      Confirmed?       │
         │   │         │
        Yes  No ───────┘
         │
         ▼
       Fix It
```

## Phase 1: Crime Scene Investigation

### Gather Evidence
1. **The Error** - Exact error message, stack trace
2. **The Scene** - Where does it happen? (file, function, line)
3. **The Trigger** - What action causes it?
4. **The Frequency** - Always? Sometimes? Random?
5. **Recent Changes** - What changed recently? (`git log --oneline -20`)

### Key Questions
- When did this last work correctly?
- Can I reproduce it consistently?
- Does it happen in all environments?
- What's different when it works vs when it fails?

## Phase 2: Form Hypotheses

List 3-5 possible causes, ranked by likelihood:

```markdown
| # | Hypothesis | Likelihood | How to Test |
|---|-----------|------------|-------------|
| 1 | [Most likely cause] | High | [Quick test] |
| 2 | [Second guess] | Medium | [Test method] |
| 3 | [Long shot] | Low | [Test method] |
```

## Phase 3: Test Theories

### Isolation Technique
```
1. Start with the smallest reproducible case
2. Remove components until bug disappears
3. The last removed component is likely the culprit
```

### Binary Search (for regressions)
```
1. Find a commit where it worked
2. Find a commit where it's broken
3. Bisect: test the middle
4. Repeat until you find the breaking change
```

### Print Debugging (Strategic)
```typescript
console.log('=== DEBUG: functionName ===');
console.log('Input:', JSON.stringify(input, null, 2));
console.log('State:', relevantState);
// ... operation ...
console.log('Output:', result);
console.log('=== END DEBUG ===');
```

## Phase 4: Common Bug Patterns

### The Usual Suspects

| Pattern | Symptoms | Check |
|---------|----------|-------|
| **Off-by-one** | Works except edges | Loop bounds, array indices |
| **Null/undefined** | Random crashes | Optional chaining, defaults |
| **Async timing** | Works sometimes | Race conditions, await missing |
| **Stale state** | Old data shown | Closures, useEffect deps |
| **Type coercion** | Weird comparisons | `===` vs `==`, string/number |
| **Scope issues** | Wrong value | var vs let, closures |
| **Copy vs reference** | Unexpected mutations | Object/array spreading |

### Environment Gremlins
- Different Node/npm versions
- Missing environment variables
- Cached data (clear node_modules, .next, etc.)
- OS-specific path issues (/ vs \)

## Phase 5: The Fix

### Before Fixing
1. Write a test that fails due to the bug
2. Confirm test fails for the right reason
3. Make the minimal fix
4. Confirm test passes
5. Check no other tests broke

### The Fix Checklist
- [ ] Fixes root cause, not just symptom
- [ ] Doesn't break anything else
- [ ] Added test to prevent regression
- [ ] No console.logs left behind
- [ ] Commit message explains the WHY

## Report Template

```markdown
## Bug Report

**Symptom**: [What user sees]
**Root Cause**: [Why it actually happened]
**Fix**: [What was changed]
**Prevention**: [How to avoid in future]
```

## Remember

> "Debugging is like being the detective in a crime movie where you are also the murderer."

The bug is in *your* code. You wrote it. You can fix it.
