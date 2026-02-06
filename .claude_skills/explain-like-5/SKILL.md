---
name: explain-like-5
description: Explain code, concepts, or errors in simple terms - perfect for learning or explaining to non-technical stakeholders
argument-hint: [code-snippet, concept, or error-message]
allowed-tools: Read, Glob, Grep, WebSearch
disable-model-invocation: false
---

# Explain Like I'm 5

Explain this simply: **$ARGUMENTS**

## The Art of Simple Explanation

### Rules
1. **No jargon** - If you must use a technical term, explain it immediately
2. **Use analogies** - Connect to everyday experiences
3. **Build up** - Start with the simplest version, add complexity
4. **Visual when possible** - ASCII diagrams, simple examples
5. **One concept at a time** - Don't bundle multiple ideas

## Explanation Structure

### 1. The One-Liner
> "In simple terms, this [does X / means Y / happens because Z]."

### 2. The Analogy
> "Think of it like [everyday thing]..."

Good analogy sources:
- Kitchen/cooking
- Mail/packages
- Building/construction
- Traffic/roads
- Libraries/books
- Conversations between people

### 3. The Simple Example
```
// Most basic working example
// With comments on each line
```

### 4. The "Why It Matters"
> "This is important because..."
> "Without this, [bad thing] would happen..."

### 5. Common Confusions
> "People often think X, but actually Y..."

## Example Explanations

### API
> "An API is like a waiter in a restaurant. You (the app) tell the waiter (API) what you want, and they go to the kitchen (server) to get it for you. You don't need to know how to cook - you just need to know how to order."

### Async/Await
> "Imagine ordering coffee. Synchronous is like waiting at the counter until your coffee is ready - you can't do anything else. Async is like getting a buzzer - you can sit down, check your phone, and when the buzzer goes off, your coffee is ready. `await` is you choosing to wait for the buzzer."

### Database Index
> "An index is like the index in the back of a textbook. Without it, to find 'photosynthesis', you'd read every page. With an index, you look up 'photosynthesis → page 142' and go directly there."

### Git Branch
> "Imagine you're writing a story and want to try a different ending without ruining what you have. You photocopy all your pages (branch), experiment on the copy, and if you like it, you update the original (merge). If not, you just throw away the copy."

## For Code Explanations

```typescript
// WHAT THEY WROTE:
const result = items.filter(x => x.active).map(x => x.name);

// WHAT IT MEANS:
// 1. Start with a list of items
// 2. Keep only the ones where 'active' is true (filter)
// 3. From those, get just the names (map)
// 4. Result: a list of names of active items

// ANALOGY:
// Like going through a stack of resumes:
// 1. Remove anyone not currently employed (filter)
// 2. Write down just their names (map)
```

## For Error Explanations

```
ERROR: Cannot read property 'name' of undefined

SIMPLE EXPLANATION:
You tried to get the 'name' from something, but that
something doesn't exist (it's undefined).

ANALOGY:
Like trying to read the title of a book, but there's
no book there - just an empty shelf.

LIKELY CAUSE:
The variable you're accessing hasn't been set yet,
or the data you expected didn't load.

FIX PATTERN:
Check if the thing exists before accessing it:
  if (thing) { console.log(thing.name); }
Or use optional chaining:
  console.log(thing?.name);
```

## Output Format

Always structure explanations as:

1. **Simple Answer** (1-2 sentences)
2. **Analogy** (relatable comparison)
3. **Example** (if code-related)
4. **Why It Matters** (context)
5. **Watch Out For** (common mistakes, optional)
